# ==============================================================================
# File:      api/app/tests/test_sprint6.py
# Purpose:   Integration tests for Sprint 6 bug fixes: portrait field name,
#            portrait upload, character_name in members, leave table, DM
#            character creation.
# Modified:  2026-06-03
# ==============================================================================
import io
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


# ---------------------------------------------------------------------------
# 1. Portrait field name — to_dict() returns 'portrait_path'
# ---------------------------------------------------------------------------

class TestPortraitFieldName:

    def test_to_dict_returns_portrait_path(self, client, db):
        """to_dict() must include 'portrait_path' (not 'portrait_url')."""
        owner = _register_and_login(client, 'pf_dm', 'pf_dm@example.com')
        table = _create_table(client, owner)
        table_id = table['id']

        resp = client.post(f'/api/tables/{table_id}/characters',
                           json={'name': 'Frodo'},
                           headers=owner)
        assert resp.status_code == 201
        data = resp.get_json()
        assert 'portrait_path' in data
        assert 'portrait_url' not in data

    def test_portrait_path_default_none(self, client, db):
        """New character should have portrait_path=None."""
        owner = _register_and_login(client, 'pf_dm2', 'pf_dm2@example.com')
        table = _create_table(client, owner)
        table_id = table['id']

        resp = client.post(f'/api/tables/{table_id}/characters',
                           json={'name': 'Sam'},
                           headers=owner)
        data = resp.get_json()
        assert data['portrait_path'] is None


# ---------------------------------------------------------------------------
# 2. Portrait upload — multipart 'portrait' field accepted
# ---------------------------------------------------------------------------

class TestPortraitUpload:

    def _make_png_bytes(self):
        """Create a minimal valid PNG image in memory."""
        from PIL import Image
        buf = io.BytesIO()
        img = Image.new('RGB', (100, 100), color='red')
        img.save(buf, 'PNG')
        buf.seek(0)
        return buf

    def test_upload_portrait_succeeds(self, client, db):
        """POST portrait as 'portrait' multipart field returns 200."""
        owner = _register_and_login(client, 'pu_dm', 'pu_dm@example.com')
        table = _create_table(client, owner)
        table_id = table['id']

        create_resp = client.post(f'/api/tables/{table_id}/characters',
                                  json={'name': 'Aragorn'},
                                  headers=owner)
        char_id = create_resp.get_json()['id']

        data = {
            'portrait': (self._make_png_bytes(), 'portrait.png'),
        }
        resp = client.post(
            f'/api/tables/{table_id}/characters/{char_id}/portrait',
            data=data,
            content_type='multipart/form-data',
            headers=owner,
        )
        assert resp.status_code == 200
        result = resp.get_json()
        assert result['portrait_path'] is not None
        assert 'portraits/' in result['portrait_path']

    def test_upload_wrong_field_name_fails(self, client, db):
        """POST with wrong multipart field name ('file') returns 400."""
        owner = _register_and_login(client, 'pu_dm2', 'pu_dm2@example.com')
        table = _create_table(client, owner)
        table_id = table['id']

        create_resp = client.post(f'/api/tables/{table_id}/characters',
                                  json={'name': 'Legolas'},
                                  headers=owner)
        char_id = create_resp.get_json()['id']

        data = {
            'file': (self._make_png_bytes(), 'portrait.png'),
        }
        resp = client.post(
            f'/api/tables/{table_id}/characters/{char_id}/portrait',
            data=data,
            content_type='multipart/form-data',
            headers=owner,
        )
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# 3. Character name in members — GET /api/tables/<id> includes character_name
# ---------------------------------------------------------------------------

class TestCharacterNameInMembers:

    def test_member_has_character_name(self, client, db):
        """GET table detail includes character_name for members with chars."""
        owner = _register_and_login(client, 'cn_dm', 'cn_dm@example.com')
        player = _register_and_login(client, 'cn_player', 'cn_player@example.com')

        table = _create_table(client, owner)
        table_id = table['id']
        _join_table(client, player, table['invite_code'])

        # Player creates a character
        client.post(f'/api/tables/{table_id}/characters',
                    json={'name': 'Gimli'},
                    headers=player)

        resp = client.get(f'/api/tables/{table_id}', headers=owner)
        assert resp.status_code == 200
        members = resp.get_json()['members']

        player_member = [m for m in members if m['role'] == 'player'][0]
        assert player_member['character_name'] == 'Gimli'

    def test_member_without_character_has_null_name(self, client, db):
        """character_name is null for members without a character."""
        owner = _register_and_login(client, 'cn_dm2', 'cn_dm2@example.com')
        player = _register_and_login(client, 'cn_player2', 'cn_player2@example.com')

        table = _create_table(client, owner)
        table_id = table['id']
        _join_table(client, player, table['invite_code'])

        resp = client.get(f'/api/tables/{table_id}', headers=owner)
        members = resp.get_json()['members']

        player_member = [m for m in members if m['role'] == 'player'][0]
        assert player_member['character_name'] is None


# ---------------------------------------------------------------------------
# 4. Leave table — DELETE /api/tables/<id>/leave
# ---------------------------------------------------------------------------

class TestLeaveTable:

    def test_player_can_leave(self, client, db):
        """Player leaves table — 200, membership removed."""
        owner = _register_and_login(client, 'lt_dm', 'lt_dm@example.com')
        player = _register_and_login(client, 'lt_player', 'lt_player@example.com')

        table = _create_table(client, owner)
        table_id = table['id']
        _join_table(client, player, table['invite_code'])

        resp = client.delete(f'/api/tables/{table_id}/leave', headers=player)
        assert resp.status_code == 200

        # Verify player is no longer a member
        detail = client.get(f'/api/tables/{table_id}', headers=player)
        assert detail.status_code == 403  # no longer a member

    def test_leave_removes_character(self, client, db):
        """Leaving a table also removes the player's character."""
        owner = _register_and_login(client, 'lt_dm2', 'lt_dm2@example.com')
        player = _register_and_login(client, 'lt_player2', 'lt_player2@example.com')

        table = _create_table(client, owner)
        table_id = table['id']
        _join_table(client, player, table['invite_code'])

        # Create character
        client.post(f'/api/tables/{table_id}/characters',
                    json={'name': 'Boromir'},
                    headers=player)

        # Leave
        client.delete(f'/api/tables/{table_id}/leave', headers=player)

        # Verify character is gone
        chars = client.get(f'/api/tables/{table_id}/characters', headers=owner)
        names = [c['name'] for c in chars.get_json()['characters']]
        assert 'Boromir' not in names

    def test_owner_cannot_leave(self, client, db):
        """Owner trying to leave returns 400."""
        owner = _register_and_login(client, 'lt_dm3', 'lt_dm3@example.com')
        table = _create_table(client, owner)
        table_id = table['id']

        resp = client.delete(f'/api/tables/{table_id}/leave', headers=owner)
        assert resp.status_code == 400
        assert 'owner' in resp.get_json()['error'].lower()

    def test_non_member_cannot_leave(self, client, db):
        """Non-member trying to leave returns 404."""
        owner = _register_and_login(client, 'lt_dm4', 'lt_dm4@example.com')
        outsider = _register_and_login(client, 'lt_outsider', 'lt_outsider@example.com')

        table = _create_table(client, owner)
        table_id = table['id']

        resp = client.delete(f'/api/tables/{table_id}/leave', headers=outsider)
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 5. DM character creation — table owner can create a character
# ---------------------------------------------------------------------------

class TestDMCharacterCreation:

    def test_owner_can_create_character(self, client, db):
        """Table owner (DM) can POST to create a character on their table."""
        owner = _register_and_login(client, 'dc_dm', 'dc_dm@example.com')
        table = _create_table(client, owner)
        table_id = table['id']

        resp = client.post(f'/api/tables/{table_id}/characters',
                           json={'name': 'DMPC', 'description': 'A DM character'},
                           headers=owner)
        assert resp.status_code == 201
        data = resp.get_json()
        assert data['name'] == 'DMPC'
        assert data['table_id'] == table_id

    def test_owner_character_shows_in_list(self, client, db):
        """DM's character shows up in the characters list for the table."""
        owner = _register_and_login(client, 'dc_dm2', 'dc_dm2@example.com')
        player = _register_and_login(client, 'dc_player', 'dc_player@example.com')

        table = _create_table(client, owner)
        table_id = table['id']
        _join_table(client, player, table['invite_code'])

        # Both create characters
        client.post(f'/api/tables/{table_id}/characters',
                    json={'name': 'DM NPC'},
                    headers=owner)
        client.post(f'/api/tables/{table_id}/characters',
                    json={'name': 'Player Hero'},
                    headers=player)

        resp = client.get(f'/api/tables/{table_id}/characters', headers=owner)
        assert resp.status_code == 200
        names = [c['name'] for c in resp.get_json()['characters']]
        assert 'DM NPC' in names
        assert 'Player Hero' in names
