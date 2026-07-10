# ==============================================================================
# File:      api/app/tests/test_history.py
# Purpose:   Integration tests for session history routes (GET /api/sessions,
#            GET /api/sessions/{id}/scenes). Covers listing, empty state,
#            scene retrieval, ownership checks, and pagination.
# Modified:  2026-06-01
# ==============================================================================
import pytest
from datetime import datetime
from app.models.session import Session
from app.models.scene import Scene
from app.models.user import User
from app import db as _db


def _make_user(db_session, username, email):
    """Insert a minimal User and return it."""
    user = User(
        username=username,
        email=email,
        password_hash='fakehash',
    )
    db_session.add(user)
    db_session.commit()
    return user


def _make_session(db_session, user_id, status='ended'):
    """Insert a Session for the given user."""
    s = Session(
        user_id=user_id,
        status=status,
        started_at=datetime.utcnow(),
    )
    db_session.add(s)
    db_session.commit()
    return s


def _make_scene(db_session, session_id, desc='A scene'):
    """Insert a Scene for the given session."""
    sc = Scene(
        session_id=session_id,
        image_url='https://example.com/img.png',
        prompt='test prompt',
        scene_description=desc,
    )
    db_session.add(sc)
    db_session.commit()
    return sc


class TestListSessions:
    """GET /api/sessions — list user's past sessions."""

    def test_returns_users_sessions(self, client, db, auth_headers):
        """1. Returns sessions belonging to the authenticated user."""
        # The auth_headers fixture creates a user; start+end a session via API
        resp = client.post('/api/session/start', json={
            'game_type': 'fantasy_dnd',
        }, headers=auth_headers)
        token = resp.get_json()['session_token']
        client.post('/api/session/end', json={
            'session_token': token,
        }, headers=auth_headers)

        resp = client.get('/api/sessions', headers=auth_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'sessions' in data
        assert len(data['sessions']) >= 1
        assert data['total'] >= 1

    def test_returns_empty_list_for_new_user(self, client, db, auth_headers):
        """2. Returns empty list when the user has no sessions."""
        # Fresh user from auth_headers, no sessions created
        # We need a *different* user than the one that may have sessions from
        # other tests.  Register a new one.
        client.post('/api/auth/register', json={
            'username': 'newhistuser',
            'email': 'newhist@example.com',
            'password': 'password123',
        })
        login = client.post('/api/auth/login', json={
            'username': 'newhistuser',
            'password': 'password123',
        })
        headers = {
            'Authorization': f"Bearer {login.get_json()['token']}"
        }

        resp = client.get('/api/sessions', headers=headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['sessions'] == []
        assert data['total'] == 0


class TestListSessionScenes:
    """GET /api/sessions/{id}/scenes — list scenes for a session."""

    def test_returns_scenes(self, client, db, auth_headers):
        """3. Returns scenes for the user's own session."""
        # Start a session, then directly insert a scene
        resp = client.post('/api/session/start', json={}, headers=auth_headers)
        session_data = resp.get_json()
        session = Session.query.filter_by(
            session_token=session_data['session_token']
        ).first()

        _make_scene(_db.session, session.id, desc='Dark cave')

        resp = client.get(
            f'/api/sessions/{session.id}/scenes', headers=auth_headers
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data['scenes']) == 1
        assert data['scenes'][0]['scene_description'] == 'Dark cave'

    def test_returns_403_for_other_users_session(self, client, db, auth_headers):
        """4. Returns 403 when accessing another user's session."""
        # Create a second user and a session owned by them
        other_user = _make_user(
            _db.session, 'otherowner', 'other@example.com'
        )
        other_session = _make_session(_db.session, other_user.id)

        resp = client.get(
            f'/api/sessions/{other_session.id}/scenes',
            headers=auth_headers,
        )
        assert resp.status_code == 403

    def test_pagination_works(self, client, db, auth_headers):
        """5. Pagination returns correct page metadata."""
        resp = client.post('/api/session/start', json={}, headers=auth_headers)
        session_data = resp.get_json()
        session = Session.query.filter_by(
            session_token=session_data['session_token']
        ).first()

        # Insert 3 scenes
        for i in range(3):
            _make_scene(_db.session, session.id, desc=f'Scene {i}')

        # Request page 1 with per_page=2
        resp = client.get(
            f'/api/sessions/{session.id}/scenes?page=1&per_page=2',
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data['scenes']) == 2
        assert data['total'] == 3
        assert data['pages'] == 2
        assert data['page'] == 1
