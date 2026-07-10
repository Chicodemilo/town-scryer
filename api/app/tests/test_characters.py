# ==============================================================================
# File:      api/app/tests/test_characters.py
# Purpose:   Integration tests for player character CRUD, ownership enforcement,
#            per-table uniqueness, and table-owner delete privileges.
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
    """Create a table and return response data."""
    resp = client.post('/api/tables', json={'name': name}, headers=headers)
    return resp.get_json()


def _join_table(client, headers, invite_code):
    """Join a table via invite code."""
    return client.post('/api/tables/join',
                       json={'invite_code': invite_code},
                       headers=headers)


class TestCreateCharacter:

    def test_create_character(self, client, db):
        """1. Create character for a table -- returns character with table_id."""
        owner = _register_and_login(client, 'cdm1', 'cdm1@example.com')
        table = _create_table(client, owner)
        table_id = table['id']

        resp = client.post(f'/api/tables/{table_id}/characters',
                           json={'name': 'Gandalf', 'description': 'A wise wizard'},
                           headers=owner)
        assert resp.status_code == 201
        data = resp.get_json()
        assert data['name'] == 'Gandalf'
        assert data['table_id'] == table_id
        assert data['description'] == 'A wise wizard'

    def test_one_character_per_user_per_table(self, client, db):
        """2. One character per user per table -- second create fails."""
        owner = _register_and_login(client, 'cdm2', 'cdm2@example.com')
        table = _create_table(client, owner)
        table_id = table['id']

        client.post(f'/api/tables/{table_id}/characters',
                    json={'name': 'Char1'},
                    headers=owner)

        resp = client.post(f'/api/tables/{table_id}/characters',
                           json={'name': 'Char2'},
                           headers=owner)
        assert resp.status_code == 409
        assert 'already' in resp.get_json()['error'].lower()


class TestUpdateCharacter:

    def test_update_own_character(self, client, db):
        """3. Update own character -- works."""
        owner = _register_and_login(client, 'cdm3', 'cdm3@example.com')
        table = _create_table(client, owner)
        table_id = table['id']

        create_resp = client.post(f'/api/tables/{table_id}/characters',
                                  json={'name': 'OldName'},
                                  headers=owner)
        char_id = create_resp.get_json()['id']

        resp = client.put(f'/api/tables/{table_id}/characters/{char_id}',
                          json={'name': 'NewName', 'description': 'Updated'},
                          headers=owner)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['name'] == 'NewName'
        assert data['description'] == 'Updated'

    def test_update_someone_elses_character(self, client, db):
        """4. Update someone else's character -- 403 (except the table owner/DM)."""
        owner = _register_and_login(client, 'cdm4', 'cdm4@example.com')
        player = _register_and_login(client, 'cplayer4', 'cplayer4@example.com')
        other = _register_and_login(client, 'cother4', 'cother4@example.com')

        table = _create_table(client, owner)
        table_id = table['id']
        _join_table(client, player, table['invite_code'])
        _join_table(client, other, table['invite_code'])

        # Player creates their character
        create_resp = client.post(f'/api/tables/{table_id}/characters',
                                  json={'name': 'PlayerChar'},
                                  headers=player)
        char_id = create_resp.get_json()['id']

        # Another player (not the claimer, not the DM) tries to update it
        resp = client.put(f'/api/tables/{table_id}/characters/{char_id}',
                          json={'name': 'Hacked'},
                          headers=other)
        assert resp.status_code == 403

        # The table owner (DM) is allowed to edit any character on their table
        resp = client.put(f'/api/tables/{table_id}/characters/{char_id}',
                          json={'name': 'DM Adjusted'},
                          headers=owner)
        assert resp.status_code == 200
        assert resp.get_json()['name'] == 'DM Adjusted'


class TestListCharacters:

    def test_list_characters_any_member(self, client, db):
        """5. List characters for table -- any member can view all."""
        owner = _register_and_login(client, 'cdm5', 'cdm5@example.com')
        player = _register_and_login(client, 'cplayer5', 'cplayer5@example.com')

        table = _create_table(client, owner)
        table_id = table['id']
        _join_table(client, player, table['invite_code'])

        # Both create characters
        client.post(f'/api/tables/{table_id}/characters',
                    json={'name': 'DM Char'},
                    headers=owner)
        client.post(f'/api/tables/{table_id}/characters',
                    json={'name': 'Player Char'},
                    headers=player)

        # Player can see all characters
        resp = client.get(f'/api/tables/{table_id}/characters', headers=player)
        assert resp.status_code == 200
        chars = resp.get_json()['characters']
        names = [c['name'] for c in chars]
        assert 'DM Char' in names
        assert 'Player Char' in names
        assert len(chars) == 2


class TestDeleteCharacter:

    def test_delete_own_character(self, client, db):
        """6. Delete own character -- works."""
        owner = _register_and_login(client, 'cdm6', 'cdm6@example.com')
        player = _register_and_login(client, 'cplayer6', 'cplayer6@example.com')

        table = _create_table(client, owner)
        table_id = table['id']
        _join_table(client, player, table['invite_code'])

        create_resp = client.post(f'/api/tables/{table_id}/characters',
                                  json={'name': 'ToDelete'},
                                  headers=player)
        char_id = create_resp.get_json()['id']

        resp = client.delete(f'/api/tables/{table_id}/characters/{char_id}',
                             headers=player)
        assert resp.status_code == 200
        assert 'deleted' in resp.get_json()['message'].lower()

    def test_table_owner_can_delete_any_character(self, client, db):
        """7. Table owner can delete any character."""
        owner = _register_and_login(client, 'cdm7', 'cdm7@example.com')
        player = _register_and_login(client, 'cplayer7', 'cplayer7@example.com')

        table = _create_table(client, owner)
        table_id = table['id']
        _join_table(client, player, table['invite_code'])

        create_resp = client.post(f'/api/tables/{table_id}/characters',
                                  json={'name': 'PlayerChar'},
                                  headers=player)
        char_id = create_resp.get_json()['id']

        # Owner deletes player's character
        resp = client.delete(f'/api/tables/{table_id}/characters/{char_id}',
                             headers=owner)
        assert resp.status_code == 200


class TestNonMemberAccess:

    def test_non_member_cant_access_characters(self, client, db):
        """8. Non-member can't access characters."""
        owner = _register_and_login(client, 'cdm8', 'cdm8@example.com')
        outsider = _register_and_login(client, 'outsider8', 'outsider8@example.com')

        table = _create_table(client, owner)
        table_id = table['id']

        # Outsider tries to list characters
        resp = client.get(f'/api/tables/{table_id}/characters', headers=outsider)
        assert resp.status_code == 403

        # Outsider tries to create a character
        resp = client.post(f'/api/tables/{table_id}/characters',
                           json={'name': 'Intruder'},
                           headers=outsider)
        assert resp.status_code == 403
