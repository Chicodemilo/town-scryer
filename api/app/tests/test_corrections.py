# ==============================================================================
# File:      api/app/tests/test_corrections.py
# Purpose:   Tests for DM correction endpoints — add, list, delete, clear,
#            prompt inclusion, and cross-user access denial.
# Modified:  2026-06-01
# ==============================================================================
import pytest
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _start_session(client, auth_headers, **kwargs):
    """Start a session and return (response, data)."""
    payload = {
        'game_type': 'fantasy_dnd',
        'art_style': 'frazetta',
        'rating': 'PG-13',
    }
    payload.update(kwargs)
    resp = client.post('/api/session/start', json=payload, headers=auth_headers)
    return resp, resp.get_json()


def _register_and_login(client, username, email, password='password123'):
    """Register a new user and return auth headers."""
    client.post('/api/auth/register', json={
        'username': username,
        'email': email,
        'password': password,
    })
    resp = client.post('/api/auth/login', json={
        'username': username,
        'password': password,
    })
    token = resp.get_json()['token']
    return {'Authorization': f'Bearer {token}'}


# ===========================================================================
# Tests
# ===========================================================================

class TestCorrections:

    def test_add_correction(self, client, db, auth_headers):
        """1. Add correction — creates record, returns list."""
        _, start_data = _start_session(client, auth_headers)
        token = start_data['session_token']

        resp = client.post('/api/session/correction',
                           json={'session_token': token, 'text': 'The dragon is blue, not red'},
                           headers=auth_headers)
        assert resp.status_code == 201
        data = resp.get_json()
        assert 'correction' in data
        assert data['correction']['text'] == 'The dragon is blue, not red'
        assert 'corrections' in data
        assert len(data['corrections']) == 1

    def test_list_corrections(self, client, db, auth_headers):
        """2. List corrections — returns all for session."""
        _, start_data = _start_session(client, auth_headers)
        token = start_data['session_token']

        # Add two corrections
        client.post('/api/session/correction',
                    json={'session_token': token, 'text': 'Correction one'},
                    headers=auth_headers)
        client.post('/api/session/correction',
                    json={'session_token': token, 'text': 'Correction two'},
                    headers=auth_headers)

        resp = client.get(f'/api/session/corrections?session_token={token}',
                          headers=auth_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data['corrections']) == 2
        texts = [c['text'] for c in data['corrections']]
        assert 'Correction one' in texts
        assert 'Correction two' in texts

    def test_delete_single_correction(self, client, db, auth_headers):
        """3. Delete single correction — removes it."""
        _, start_data = _start_session(client, auth_headers)
        token = start_data['session_token']

        add_resp = client.post('/api/session/correction',
                               json={'session_token': token, 'text': 'Delete me'},
                               headers=auth_headers)
        correction_id = add_resp.get_json()['correction']['id']

        resp = client.delete(f'/api/session/correction/{correction_id}',
                             headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.get_json()['corrections']) == 0

    def test_clear_all_corrections(self, client, db, auth_headers):
        """4. Clear all corrections — empties list."""
        _, start_data = _start_session(client, auth_headers)
        token = start_data['session_token']

        # Add a couple
        client.post('/api/session/correction',
                    json={'session_token': token, 'text': 'First'},
                    headers=auth_headers)
        client.post('/api/session/correction',
                    json={'session_token': token, 'text': 'Second'},
                    headers=auth_headers)

        resp = client.post('/api/session/corrections/clear',
                           json={'session_token': token},
                           headers=auth_headers)
        assert resp.status_code == 200
        assert resp.get_json()['corrections'] == []

    @patch('app.services.scene_service.anthropic')
    @patch('app.services.scene_service.generate_image')
    def test_corrections_appear_in_extraction_prompt(
        self, mock_gen_image, mock_anthropic, client, db, auth_headers
    ):
        """5. Corrections appear in scene extraction prompt (mock Claude,
        verify system prompt contains correction text)."""
        # Set up mock Anthropic
        mock_message = MagicMock()
        mock_message.content = [
            MagicMock(text='{"scene_changed": false, '
                           '"scene_description": "A tavern", '
                           '"image_prompt": ""}')
        ]
        mock_client_instance = MagicMock()
        mock_client_instance.messages.create.return_value = mock_message
        mock_anthropic.Anthropic.return_value = mock_client_instance

        _, start_data = _start_session(client, auth_headers)
        token = start_data['session_token']

        # Add a correction
        client.post('/api/session/correction',
                    json={'session_token': token,
                          'text': 'The tavern has a secret basement'},
                    headers=auth_headers)

        # Send a chunk — this triggers scene analysis with Claude
        resp = client.post('/api/session/chunk',
                           json={'session_token': token,
                                 'transcript': 'The party looks around the room...'},
                           headers=auth_headers)
        assert resp.status_code == 200

        # Verify the system prompt sent to Claude contains the correction
        call_kwargs = mock_client_instance.messages.create.call_args
        system_prompt = call_kwargs.kwargs.get('system', '')
        assert 'The tavern has a secret basement' in system_prompt
        assert 'DM CORRECTIONS' in system_prompt

    def test_cant_add_correction_to_other_users_session(self, client, db, auth_headers):
        """6. Can't add correction to another user's session."""
        # User 1 starts a session
        _, start_data = _start_session(client, auth_headers)
        token = start_data['session_token']

        # User 2 tries to add a correction to User 1's session
        other_headers = _register_and_login(client, 'otheruser', 'other@example.com')

        resp = client.post('/api/session/correction',
                           json={'session_token': token, 'text': 'Hacking attempt'},
                           headers=other_headers)
        assert resp.status_code == 404
        assert 'error' in resp.get_json()
