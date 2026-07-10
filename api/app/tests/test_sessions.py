# ==============================================================================
# File:      api/app/tests/test_sessions.py
# Purpose:   Integration tests for session lifecycle, chunk processing, and
#            edge cases (stale heartbeat, invalid tokens, etc.).
# Modified:  2026-06-01
# ==============================================================================
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _start_session(client, auth_headers, **kwargs):
    """Helper: start a session and return (response, data)."""
    payload = {
        'game_type': 'fantasy_dnd',
        'art_style': 'frazetta',
        'rating': 'PG-13',
    }
    payload.update(kwargs)
    resp = client.post('/api/session/start', json=payload, headers=auth_headers)
    return resp, resp.get_json()


# ===========================================================================
# 1-8: Session lifecycle
# ===========================================================================

class TestSessionLifecycle:
    """Tests for starting, pausing, resuming, ending, and querying sessions."""

    def test_start_session(self, client, db, auth_headers):
        """1. Start session -- returns session_token, status=active."""
        resp, data = _start_session(client, auth_headers)
        assert resp.status_code == 201
        assert 'session_token' in data
        assert data['status'] == 'active'
        assert data['game_type'] == 'fantasy_dnd'

    def test_start_session_conflict(self, client, db, auth_headers):
        """2. Start session when one already active -- returns 409."""
        _start_session(client, auth_headers)
        resp, data = _start_session(client, auth_headers)
        assert resp.status_code == 409
        assert 'error' in data

    def test_pause_session(self, client, db, auth_headers):
        """3. Pause session -- status changes to paused."""
        _, start_data = _start_session(client, auth_headers)
        token = start_data['session_token']

        resp = client.post('/api/session/pause',
                           json={'session_token': token},
                           headers=auth_headers)
        assert resp.status_code == 200
        assert resp.get_json()['status'] == 'paused'

    def test_resume_session(self, client, db, auth_headers):
        """4. Resume session -- status changes to active."""
        _, start_data = _start_session(client, auth_headers)
        token = start_data['session_token']

        # Pause first
        client.post('/api/session/pause',
                    json={'session_token': token},
                    headers=auth_headers)

        # Resume
        resp = client.post('/api/session/resume',
                           json={'session_token': token},
                           headers=auth_headers)
        assert resp.status_code == 200
        assert resp.get_json()['status'] == 'active'

    def test_end_session(self, client, db, auth_headers):
        """5. End session -- status=ended, returns stats."""
        _, start_data = _start_session(client, auth_headers)
        token = start_data['session_token']

        resp = client.post('/api/session/end',
                           json={'session_token': token},
                           headers=auth_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['status'] == 'ended'
        assert 'image_count' in data
        assert 'duration_seconds' in data

    def test_heartbeat(self, client, db, auth_headers):
        """6. Heartbeat -- updates last_heartbeat."""
        _, start_data = _start_session(client, auth_headers)
        token = start_data['session_token']

        resp = client.post('/api/session/heartbeat',
                           json={'session_token': token},
                           headers=auth_headers)
        assert resp.status_code == 200
        assert resp.get_json()['status'] == 'ok'

    def test_get_current_session(self, client, db, auth_headers):
        """7. Get current session -- returns active session."""
        _, start_data = _start_session(client, auth_headers)

        resp = client.get('/api/session/current', headers=auth_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['session_token'] == start_data['session_token']
        assert data['status'] in ('active', 'paused')

    def test_get_current_session_none(self, client, db, auth_headers):
        """8. Get current session when none -- returns 404."""
        resp = client.get('/api/session/current', headers=auth_headers)
        assert resp.status_code == 404


# ===========================================================================
# 9-11: Scenes and stale heartbeat
# ===========================================================================

class TestScenesAndStale:

    def test_latest_scene_none(self, client, db, auth_headers):
        """9. Latest scene -- returns null when no scenes."""
        _start_session(client, auth_headers)

        resp = client.get('/api/session/latest-scene', headers=auth_headers)
        assert resp.status_code == 200
        assert resp.get_json()['image_url'] is None

    def test_invalid_session_token(self, client, db, auth_headers):
        """10. Invalid session token -- returns error."""
        resp = client.post('/api/session/pause',
                           json={'session_token': 'bogus-token-does-not-exist'},
                           headers=auth_headers)
        assert resp.status_code == 400
        assert 'error' in resp.get_json()

    def test_stale_heartbeat_auto_pause(self, client, db, auth_headers):
        """11. Stale heartbeat auto-pause -- session with old heartbeat gets
        auto-paused when queried."""
        _, start_data = _start_session(client, auth_headers)
        token = start_data['session_token']

        # Manually push the heartbeat back in time to simulate staleness
        from app.models.session import Session
        session = Session.query.filter_by(session_token=token).first()
        session.last_heartbeat = datetime.utcnow() - timedelta(minutes=5)
        db.session.commit()

        # Querying the current session should trigger auto-pause
        resp = client.get('/api/session/current', headers=auth_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['status'] == 'paused'


# ===========================================================================
# 12-13: Chunk endpoint (mock external APIs)
# ===========================================================================

class TestChunkEndpoint:

    @patch('app.services.scene_service.anthropic')
    @patch('app.services.scene_service.generate_image')
    def test_send_chunk_scene_changed(self, mock_gen_image, mock_anthropic,
                                      client, db, auth_headers):
        """12. Send chunk with valid transcript -- returns scene_changed response."""
        # Set up the mock Anthropic client. scene_change_evidence must quote
        # a phrase from the transcript to survive the server-side evidence
        # check (TS-40) — otherwise scene_changed is demoted to false.
        mock_message = MagicMock()
        mock_message.content = [
            MagicMock(text='{"scene_changed": true, '
                           '"scene_change_evidence": "You enter a dark cave", '
                           '"scene_description": "A dark cave", '
                           '"image_prompt": "dark cave painting"}')
        ]
        mock_client_instance = MagicMock()
        mock_client_instance.messages.create.return_value = mock_message
        mock_anthropic.Anthropic.return_value = mock_client_instance

        # Mock image generation
        mock_gen_image.return_value = {
            'image_url': 'https://example.com/image.png',
            'image_path': '/tmp/image.png',
            'scene_description': 'A dark cave',
            'generation_time_ms': 100,
        }

        _, start_data = _start_session(client, auth_headers)
        token = start_data['session_token']

        resp = client.post('/api/session/chunk',
                           json={
                               'session_token': token,
                               'transcript': 'You enter a dark cave...',
                           },
                           headers=auth_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['scene_changed'] is True
        assert data['scene_description'] == 'A dark cave'
        assert data['image_url'] == 'https://example.com/image.png'

    @patch('app.services.scene_service.anthropic')
    def test_send_chunk_on_paused_session(self, mock_anthropic,
                                          client, db, auth_headers):
        """13. Send chunk on paused session -- returns error."""
        _, start_data = _start_session(client, auth_headers)
        token = start_data['session_token']

        # Pause the session first
        client.post('/api/session/pause',
                    json={'session_token': token},
                    headers=auth_headers)

        resp = client.post('/api/session/chunk',
                           json={
                               'session_token': token,
                               'transcript': 'Hello there',
                           },
                           headers=auth_headers)
        assert resp.status_code == 400
        assert 'not active' in resp.get_json()['error']


# ===========================================================================
# Extra edge-case tests
# ===========================================================================

class TestEdgeCases:

    def test_pause_missing_token(self, client, db, auth_headers):
        """Missing session_token in request body returns 400."""
        resp = client.post('/api/session/pause',
                           json={},
                           headers=auth_headers)
        assert resp.status_code == 400

    def test_end_already_ended(self, client, db, auth_headers):
        """Ending an already-ended session returns error."""
        _, start_data = _start_session(client, auth_headers)
        token = start_data['session_token']

        client.post('/api/session/end',
                    json={'session_token': token},
                    headers=auth_headers)

        resp = client.post('/api/session/end',
                           json={'session_token': token},
                           headers=auth_headers)
        assert resp.status_code == 400
        assert 'error' in resp.get_json()

    def test_heartbeat_on_paused_session(self, client, db, auth_headers):
        """Heartbeat on a paused session returns error."""
        _, start_data = _start_session(client, auth_headers)
        token = start_data['session_token']

        client.post('/api/session/pause',
                    json={'session_token': token},
                    headers=auth_headers)

        resp = client.post('/api/session/heartbeat',
                           json={'session_token': token},
                           headers=auth_headers)
        assert resp.status_code == 400

    def test_resume_active_session_error(self, client, db, auth_headers):
        """Resuming an already-active session returns error."""
        _, start_data = _start_session(client, auth_headers)
        token = start_data['session_token']

        resp = client.post('/api/session/resume',
                           json={'session_token': token},
                           headers=auth_headers)
        assert resp.status_code == 400

    def test_chunk_missing_transcript(self, client, db, auth_headers):
        """Chunk endpoint without transcript returns 400."""
        _, start_data = _start_session(client, auth_headers)
        token = start_data['session_token']

        resp = client.post('/api/session/chunk',
                           json={'session_token': token},
                           headers=auth_headers)
        assert resp.status_code == 400

    def test_no_auth_returns_401(self, client, db):
        """Session endpoints without auth token return 401."""
        resp = client.post('/api/session/start', json={})
        assert resp.status_code == 401
