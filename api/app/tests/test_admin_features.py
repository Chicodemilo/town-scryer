import pytest


def register_admin(client):
    """Register a user and make them admin, returning a valid admin token."""
    from app.models.user import User
    from app import db as _db
    resp = client.post('/api/auth/register', json={
        'username': f'admin{User.query.count()}',
        'email': f'admin{User.query.count()}@example.com',
        'password': 'password123',
    })
    data = resp.get_json()
    user = User.query.filter_by(username=data['user']['username']).first()
    user.is_admin = True
    _db.session.commit()
    # Re-login to get token with is_admin=True
    resp = client.post('/api/auth/login', json={
        'username': user.username,
        'password': 'password123',
    })
    token = resp.get_json()['token']
    return token, user


def test_invite_user(client, db):
    token, _ = register_admin(client)
    headers = {'Authorization': f'Bearer {token}'}

    resp = client.post('/api/admin/invite', json={'email': 'invited@example.com'}, headers=headers)
    assert resp.status_code == 201
    assert 'user' in resp.get_json()


def test_invite_duplicate_email(client, db):
    token, _ = register_admin(client)
    headers = {'Authorization': f'Bearer {token}'}

    # Register existing user
    client.post('/api/auth/register', json={
        'username': 'existinginv',
        'email': 'existing@example.com',
        'password': 'password123',
    })

    resp = client.post('/api/admin/invite', json={'email': 'existing@example.com'}, headers=headers)
    assert resp.status_code == 400


def test_complete_invite(client, db):
    token, _ = register_admin(client)
    headers = {'Authorization': f'Bearer {token}'}

    client.post('/api/admin/invite', json={'email': 'complete@example.com'}, headers=headers)

    from app.models.user import User
    user = User.query.filter_by(email='complete@example.com').first()
    invite_token = user.invite_token

    resp = client.post('/api/auth/complete-invite', json={
        'token': invite_token,
        'username': 'completeduser',
        'password': 'newpass123',
    })
    assert resp.status_code == 200
    assert resp.get_json()['user']['username'] == 'completeduser'
    assert 'token' in resp.get_json()


def test_list_admin_users(client, db):
    token, admin_user = register_admin(client)
    headers = {'Authorization': f'Bearer {token}'}

    resp = client.get('/api/admin/admin-users', headers=headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert any(u['username'] == admin_user.username for u in data['users'])


def test_update_permissions(client, db):
    token, _ = register_admin(client)
    headers = {'Authorization': f'Bearer {token}'}

    # Create another admin
    from app.models.user import User
    from app import db as _db
    resp = client.post('/api/auth/register', json={
        'username': 'permtarget',
        'email': 'permtarget@example.com',
        'password': 'password123',
    })
    target = User.query.filter_by(username='permtarget').first()
    target.is_admin = True
    _db.session.commit()

    perms = {'dashboard': True, 'users': True, 'health': True, 'terms': False}
    resp = client.put(f'/api/admin/users/{target.id}/permissions', json={'permissions': perms}, headers=headers)
    assert resp.status_code == 200
    assert resp.get_json()['user']['admin_permissions']['users'] is True
    assert resp.get_json()['user']['admin_permissions']['terms'] is False


def test_update_permissions_non_admin(client, db):
    token, _ = register_admin(client)
    headers = {'Authorization': f'Bearer {token}'}

    resp = client.post('/api/auth/register', json={
        'username': 'nonadmin',
        'email': 'nonadmin@example.com',
        'password': 'password123',
    })
    from app.models.user import User
    target = User.query.filter_by(username='nonadmin').first()

    resp = client.put(f'/api/admin/users/{target.id}/permissions', json={'permissions': {'dashboard': True}}, headers=headers)
    assert resp.status_code == 400
