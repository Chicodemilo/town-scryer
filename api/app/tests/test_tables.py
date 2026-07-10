# ==============================================================================
# File:      api/app/tests/test_tables.py
# Purpose:   Integration tests for game table CRUD, invite codes, membership,
#            and owner-only operations.
# Modified:  2026-06-01
# ==============================================================================
import pytest


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
    """Create a table and return (response, data)."""
    resp = client.post('/api/tables', json={'name': name}, headers=headers)
    return resp, resp.get_json()


class TestCreateTable:

    def test_create_table_returns_invite_code_and_owner(self, client, db):
        """1. Create table -- returns table with invite_code, user is owner."""
        headers = _register_and_login(client, 'dm1', 'dm1@example.com')
        resp, data = _create_table(client, headers)

        assert resp.status_code == 201
        assert data['name'] == 'Test Table'
        assert 'invite_code' in data
        assert len(data['invite_code']) == 6
        assert data['role'] == 'owner'


class TestListTables:

    def test_list_shows_owned_and_joined(self, client, db):
        """2. List tables -- shows owned and joined tables."""
        owner_headers = _register_and_login(client, 'dm2', 'dm2@example.com')
        player_headers = _register_and_login(client, 'player2', 'player2@example.com')

        # Owner creates a table
        _, table_data = _create_table(client, owner_headers, name='Owned Table')
        invite_code = table_data['invite_code']

        # Player joins the table
        client.post('/api/tables/join',
                    json={'invite_code': invite_code},
                    headers=player_headers)

        # Player creates their own table
        _create_table(client, player_headers, name='Player Table')

        # Player should see both tables
        resp = client.get('/api/tables', headers=player_headers)
        assert resp.status_code == 200
        tables = resp.get_json()['tables']
        names = [t['name'] for t in tables]
        assert 'Owned Table' in names
        assert 'Player Table' in names
        assert len(tables) == 2


class TestJoinTable:

    def test_join_via_invite_code(self, client, db):
        """3. Join table via invite_code -- becomes player member."""
        owner_headers = _register_and_login(client, 'dm3', 'dm3@example.com')
        player_headers = _register_and_login(client, 'player3', 'player3@example.com')

        _, table_data = _create_table(client, owner_headers)
        invite_code = table_data['invite_code']

        resp = client.post('/api/tables/join',
                           json={'invite_code': invite_code},
                           headers=player_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['role'] == 'player'
        assert data['name'] == 'Test Table'

    def test_join_with_invalid_code(self, client, db):
        """4. Join with invalid code -- error."""
        headers = _register_and_login(client, 'player4', 'player4@example.com')

        resp = client.post('/api/tables/join',
                           json={'invite_code': 'XXXXXX'},
                           headers=headers)
        assert resp.status_code == 404
        assert 'error' in resp.get_json()

    def test_already_a_member(self, client, db):
        """5. Already a member -- error."""
        owner_headers = _register_and_login(client, 'dm5', 'dm5@example.com')
        player_headers = _register_and_login(client, 'player5', 'player5@example.com')

        _, table_data = _create_table(client, owner_headers)
        invite_code = table_data['invite_code']

        # Join once
        client.post('/api/tables/join',
                    json={'invite_code': invite_code},
                    headers=player_headers)

        # Try to join again
        resp = client.post('/api/tables/join',
                           json={'invite_code': invite_code},
                           headers=player_headers)
        assert resp.status_code == 409
        assert 'Already' in resp.get_json()['error']


class TestRegenerateCode:

    def test_regenerate_code_owner_only(self, client, db):
        """6. Regenerate code -- owner only, new code returned."""
        headers = _register_and_login(client, 'dm6', 'dm6@example.com')
        _, table_data = _create_table(client, headers)
        table_id = table_data['id']
        old_code = table_data['invite_code']

        resp = client.post(f'/api/tables/{table_id}/regenerate-code',
                           headers=headers)
        assert resp.status_code == 200
        new_code = resp.get_json()['invite_code']
        assert new_code != old_code
        assert len(new_code) == 6


class TestDeleteTable:

    def test_delete_table_owner_only(self, client, db):
        """7. Delete table -- owner only."""
        headers = _register_and_login(client, 'dm7', 'dm7@example.com')
        _, table_data = _create_table(client, headers)
        table_id = table_data['id']

        resp = client.delete(f'/api/tables/{table_id}', headers=headers)
        assert resp.status_code == 200
        assert 'deleted' in resp.get_json()['message'].lower()

        # Verify it's gone
        resp = client.get('/api/tables', headers=headers)
        tables = resp.get_json()['tables']
        assert len(tables) == 0


class TestNonOwnerRestrictions:

    def test_non_owner_cant_delete(self, client, db):
        """8a. Non-owner can't delete."""
        owner_headers = _register_and_login(client, 'dm8', 'dm8@example.com')
        player_headers = _register_and_login(client, 'player8', 'player8@example.com')

        _, table_data = _create_table(client, owner_headers)
        table_id = table_data['id']

        # Player joins
        client.post('/api/tables/join',
                    json={'invite_code': table_data['invite_code']},
                    headers=player_headers)

        resp = client.delete(f'/api/tables/{table_id}', headers=player_headers)
        assert resp.status_code == 403

    def test_non_owner_cant_regenerate(self, client, db):
        """8b. Non-owner can't regenerate code."""
        owner_headers = _register_and_login(client, 'dm8b', 'dm8b@example.com')
        player_headers = _register_and_login(client, 'player8b', 'player8b@example.com')

        _, table_data = _create_table(client, owner_headers)
        table_id = table_data['id']

        # Player joins
        client.post('/api/tables/join',
                    json={'invite_code': table_data['invite_code']},
                    headers=player_headers)

        resp = client.post(f'/api/tables/{table_id}/regenerate-code',
                           headers=player_headers)
        assert resp.status_code == 403
