# ==============================================================================
# File:      api/app/tests/test_regen.py
# Purpose:   Tests for the image regen endpoint — verifies new scene creation,
#            guidance prompt modification, regen_count tracking, the
#            per-session limit, remaining count reporting, edge cases, and
#            regen-info.
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


def _add_scene_to_session(db, session_token):
    """Insert a Scene row for the given session so regen has something to work with."""
    from app.models.session import Session
    from app.models.scene import Scene

    session = Session.query.filter_by(session_token=session_token).first()
    scene = Scene(
        session_id=session.id,
        image_url='https://example.com/original.png',
        image_path='/tmp/original.png',
        prompt='a dark dungeon with torchlight',
        scene_description='A dark dungeon',
        transcript_chunk='You enter the dungeon...',
    )
    db.session.add(scene)
    db.session.commit()
    return scene


# The regen route delegates to analyze_transcript_chunk (Claude + image gen),
# so tests mock that whole pipeline at the route boundary.
MOCK_ANALYZE_RESULT = {
    'scene_changed': True,
    'image_url': 'https://example.com/regen.png',
    'scene_description': 'A dark dungeon',
    'scene': {'image_url': 'https://example.com/regen.png'},
}


# ===========================================================================
# Tests
# ===========================================================================

class TestRegen:

    @patch('app.routes.sessions.analyze_transcript_chunk')
    def test_regen_creates_new_scene(self, mock_analyze, client, db, auth_headers):
        """1. Regen creates a new scene for the session."""
        mock_analyze.return_value = MOCK_ANALYZE_RESULT

        _, start_data = _start_session(client, auth_headers)
        token = start_data['session_token']
        _add_scene_to_session(db, token)

        resp = client.post('/api/session/regen',
                           json={'session_token': token},
                           headers=auth_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['image_url'] == 'https://example.com/regen.png'
        assert 'scene_description' in data

    @patch('app.routes.sessions.analyze_transcript_chunk')
    def test_regen_with_guidance_modifies_prompt(self, mock_analyze, client, db, auth_headers):
        """2. Regen with guidance appends guidance to the prompt."""
        mock_analyze.return_value = MOCK_ANALYZE_RESULT

        _, start_data = _start_session(client, auth_headers)
        token = start_data['session_token']
        _add_scene_to_session(db, token)

        resp = client.post('/api/session/regen',
                           json={'session_token': token, 'guidance': 'more fire'},
                           headers=auth_headers)
        assert resp.status_code == 200

        # Verify the transcript passed to analyze_transcript_chunk includes
        # the guidance (the route appends it to the regen directive).
        transcript_arg = mock_analyze.call_args.args[1]
        assert 'more fire' in transcript_arg

    @patch('app.routes.sessions.analyze_transcript_chunk')
    def test_regen_increments_regen_count(self, mock_analyze, client, db, auth_headers):
        """3. Regen increments regen_count on the session."""
        mock_analyze.return_value = MOCK_ANALYZE_RESULT

        _, start_data = _start_session(client, auth_headers)
        token = start_data['session_token']
        _add_scene_to_session(db, token)

        resp = client.post('/api/session/regen',
                           json={'session_token': token},
                           headers=auth_headers)
        assert resp.status_code == 200
        assert resp.get_json()['regen_count'] == 1

        # Second regen
        resp2 = client.post('/api/session/regen',
                            json={'session_token': token},
                            headers=auth_headers)
        assert resp2.status_code == 200
        assert resp2.get_json()['regen_count'] == 2

    @patch('app.routes.sessions.analyze_transcript_chunk')
    def test_regen_respects_limit(self, mock_analyze, client, db, auth_headers):
        """4. Regen respects the per-session limit — returns 429 when exceeded."""
        mock_analyze.return_value = MOCK_ANALYZE_RESULT

        _, start_data = _start_session(client, auth_headers)
        token = start_data['session_token']
        _add_scene_to_session(db, token)

        # Use up all 10 regens
        for _ in range(10):
            resp = client.post('/api/session/regen',
                               json={'session_token': token},
                               headers=auth_headers)
            assert resp.status_code == 200

        # 11th regen should be rejected
        resp = client.post('/api/session/regen',
                           json={'session_token': token},
                           headers=auth_headers)
        assert resp.status_code == 429
        data = resp.get_json()
        assert data['remaining'] == 0
        assert 'limit' in data

    @patch('app.routes.sessions.analyze_transcript_chunk')
    def test_regen_returns_remaining_count(self, mock_analyze, client, db, auth_headers):
        """5. Regen returns remaining count after each successful regen."""
        mock_analyze.return_value = MOCK_ANALYZE_RESULT

        _, start_data = _start_session(client, auth_headers)
        token = start_data['session_token']
        _add_scene_to_session(db, token)

        resp = client.post('/api/session/regen',
                           json={'session_token': token},
                           headers=auth_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['remaining_regens'] == 9  # 10 limit - 1 used

    def test_regen_no_scenes_returns_400(self, client, db, auth_headers):
        """6. Regen on session with no scenes — returns 400."""
        _, start_data = _start_session(client, auth_headers)
        token = start_data['session_token']

        resp = client.post('/api/session/regen',
                           json={'session_token': token},
                           headers=auth_headers)
        assert resp.status_code == 400
        assert 'No scene' in resp.get_json()['error']

    @patch('app.routes.sessions.analyze_transcript_chunk')
    def test_regen_info_returns_correct_counts(self, mock_analyze, client, db, auth_headers):
        """7. Regen-info endpoint returns correct counts."""
        mock_analyze.return_value = MOCK_ANALYZE_RESULT

        _, start_data = _start_session(client, auth_headers)
        token = start_data['session_token']
        _add_scene_to_session(db, token)

        # Do one regen first
        client.post('/api/session/regen',
                    json={'session_token': token},
                    headers=auth_headers)

        resp = client.get(f'/api/session/regen-info?session_token={token}',
                          headers=auth_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['regen_count'] == 1
        assert data['regen_limit'] == 10
        assert data['remaining'] == 9
