# ==============================================================================
# File:      api/app/tests/test_preferences.py
# Purpose:   Integration tests for the preferences routes (GET/POST
#            /api/preferences). Verifies default fallback, create, read-back,
#            and update behaviour.
# Modified:  2026-06-01
# ==============================================================================
import pytest


class TestPreferences:
    """Tests for GET and POST /api/preferences."""

    def test_get_preferences_returns_defaults_when_none_saved(
        self, client, db, auth_headers
    ):
        """1. GET preferences returns defaults when the user has no saved prefs."""
        resp = client.get('/api/preferences', headers=auth_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['game_type'] == 'fantasy_dnd'
        assert data['art_style'] == 'frazetta'
        assert data['rating'] == 'PG-13'

    def test_post_preferences_creates_record(self, client, db, auth_headers):
        """2. POST preferences creates a new record and returns it."""
        resp = client.post('/api/preferences', json={
            'game_type': 'horror',
            'art_style': 'comic',
            'rating': 'R',
        }, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['game_type'] == 'horror'
        assert data['art_style'] == 'comic'
        assert data['rating'] == 'R'
        assert 'id' in data

    def test_get_preferences_returns_saved_values(
        self, client, db, auth_headers
    ):
        """3. GET preferences returns previously saved values."""
        # Save first
        client.post('/api/preferences', json={
            'game_type': 'scifi',
            'art_style': 'pixel',
            'rating': 'PG',
        }, headers=auth_headers)

        # Now read back
        resp = client.get('/api/preferences', headers=auth_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['game_type'] == 'scifi'
        assert data['art_style'] == 'pixel'
        assert data['rating'] == 'PG'

    def test_post_preferences_updates_existing_record(
        self, client, db, auth_headers
    ):
        """4. POST preferences updates an existing record (upsert)."""
        # Create
        client.post('/api/preferences', json={
            'game_type': 'fantasy_dnd',
            'art_style': 'frazetta',
            'rating': 'PG-13',
        }, headers=auth_headers)

        # Update only art_style
        resp = client.post('/api/preferences', json={
            'art_style': 'watercolor',
        }, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        # art_style updated, others unchanged
        assert data['art_style'] == 'watercolor'
        assert data['game_type'] == 'fantasy_dnd'
        assert data['rating'] == 'PG-13'
