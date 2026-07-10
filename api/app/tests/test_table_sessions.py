# ==============================================================================
# File:      api/app/tests/test_table_sessions.py
# Purpose:   Integration tests for sessions linked to tables, including
#            ownership enforcement and character descriptions in scene prompts.
# Modified:  2026-06-01
# ==============================================================================
import pytest
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _register_and_login(client, username, email):
    """Register a user and return auth headers."""
    client.post('/api/auth/register', json={
        'username': username,
        'email': email,
        'password': 'password123',
    })
    resp = client.post('/api/auth/login', json={
        'username': username,
        'password': 'password123',
    })
    token = resp.get_json()['token']
    return {'Authorization': f'Bearer {token}'}


def _create_table(client, headers, name='Test Table'):
    """Create a table and return response data."""
    resp = client.post('/api/tables', json={'name': name}, headers=headers)
    return resp.get_json()


def _join_table(client, headers, invite_code):
    """Join a table via invite code."""
    return client.post('/api/tables/join',
                       json={'invite_code': invite_code},
                       headers=headers)


class TestTableSessions:

    def test_start_session_with_table_id(self, client, db):
        """9. Start session with table_id -- session linked to table."""
        owner = _register_and_login(client, 'tsdm1', 'tsdm1@example.com')
        table = _create_table(client, owner)

        resp = client.post('/api/session/start',
                           json={
                               'game_type': 'fantasy_dnd',
                               'art_style': 'frazetta',
                               'rating': 'PG-13',
                               'table_id': table['id'],
                           },
                           headers=owner)
        assert resp.status_code == 201
        data = resp.get_json()
        assert data['status'] == 'active'
        assert 'session_token' in data

    def test_start_session_non_owner_403(self, client, db):
        """10. Start session with table_id on table you don't own -- 403."""
        owner = _register_and_login(client, 'tsdm2', 'tsdm2@example.com')
        player = _register_and_login(client, 'tsplayer2', 'tsplayer2@example.com')

        table = _create_table(client, owner)
        _join_table(client, player, table['invite_code'])

        resp = client.post('/api/session/start',
                           json={
                               'game_type': 'fantasy_dnd',
                               'table_id': table['id'],
                           },
                           headers=player)
        assert resp.status_code == 403
        assert 'owner' in resp.get_json()['error'].lower()

    @patch('app.services.scene_service.anthropic')
    @patch('app.services.scene_service.generate_image')
    def test_scene_prompt_includes_characters(self, mock_gen_image,
                                              mock_anthropic, client, db):
        """11. Scene extraction includes character descriptions in the system
        prompt sent to Claude (mock Claude API, verify prompt contents)."""
        owner = _register_and_login(client, 'tsdm3', 'tsdm3@example.com')
        player = _register_and_login(client, 'tsplayer3', 'tsplayer3@example.com')

        table = _create_table(client, owner)
        table_id = table['id']
        _join_table(client, player, table['invite_code'])

        # Create characters
        client.post(f'/api/tables/{table_id}/characters',
                    json={'name': 'Aragorn', 'description': 'A rugged ranger'},
                    headers=owner)
        client.post(f'/api/tables/{table_id}/characters',
                    json={'name': 'Legolas', 'description': 'An elven archer'},
                    headers=player)

        # Set up mock Anthropic response
        mock_message = MagicMock()
        mock_message.content = [
            MagicMock(text='{"scene_changed": true, '
                           '"scene_description": "A forest clearing with Aragorn", '
                           '"image_prompt": "forest clearing painting"}')
        ]
        mock_client_instance = MagicMock()
        mock_client_instance.messages.create.return_value = mock_message
        mock_anthropic.Anthropic.return_value = mock_client_instance

        # Mock image generation
        mock_gen_image.return_value = {
            'image_url': 'https://example.com/scene.png',
            'image_path': '/tmp/scene.png',
            'scene_description': 'A forest clearing',
            'generation_time_ms': 100,
        }

        # Start session linked to table
        start_resp = client.post('/api/session/start',
                                 json={
                                     'game_type': 'fantasy_dnd',
                                     'art_style': 'frazetta',
                                     'rating': 'PG-13',
                                     'table_id': table_id,
                                 },
                                 headers=owner)
        token = start_resp.get_json()['session_token']

        # Send a transcript chunk
        client.post('/api/session/chunk',
                    json={
                        'session_token': token,
                        'transcript': 'You walk into a forest clearing...',
                    },
                    headers=owner)

        # Verify the system prompt sent to Claude contains character info
        call_args = mock_client_instance.messages.create.call_args
        system_prompt = call_args.kwargs.get('system', '')

        assert 'Aragorn' in system_prompt
        assert 'rugged ranger' in system_prompt
        assert 'Legolas' in system_prompt
        assert 'elven archer' in system_prompt
        assert 'PARTY MEMBERS' in system_prompt
