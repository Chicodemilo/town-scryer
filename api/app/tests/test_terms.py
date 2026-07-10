import pytest


def register_admin(client):
    """Register a user and make them admin, returning a valid admin token."""
    from app.models.user import User
    from app import db as _db
    resp = client.post('/api/auth/register', json={
        'username': f'tadmin{User.query.count()}',
        'email': f'tadmin{User.query.count()}@example.com',
        'password': 'password123',
    })
    data = resp.get_json()
    user = User.query.filter_by(username=data['user']['username']).first()
    user.is_admin = True
    _db.session.commit()
    resp = client.post('/api/auth/login', json={
        'username': user.username,
        'password': 'password123',
    })
    token = resp.get_json()['token']
    return token, user


def test_get_terms(client, db):
    resp = client.get('/api/auth/terms')
    assert resp.status_code == 200
    data = resp.get_json()
    assert 'terms' in data
    assert 'content' in data['terms']


def test_accept_terms(client, db):
    resp = client.post('/api/auth/register', json={
        'username': 'termsuser',
        'email': 'terms@example.com',
        'password': 'password123',
    })
    token = resp.get_json()['token']
    headers = {'Authorization': f'Bearer {token}'}

    resp = client.get('/api/auth/profile', headers=headers)
    assert resp.get_json()['user']['terms_accepted'] is False

    resp = client.put('/api/auth/accept-terms', headers=headers)
    assert resp.status_code == 200
    assert resp.get_json()['user']['terms_accepted'] is True


def test_admin_update_terms(client, db):
    token, _ = register_admin(client)
    headers = {'Authorization': f'Bearer {token}'}

    resp = client.put('/api/admin/terms', json={'content': 'New terms content here.'}, headers=headers)
    assert resp.status_code == 200
    assert resp.get_json()['terms']['content'] == 'New terms content here.'


def test_admin_reset_terms(client, db):
    token, admin_user = register_admin(client)
    headers = {'Authorization': f'Bearer {token}'}

    # Register a regular user who accepted terms
    resp = client.post('/api/auth/register', json={
        'username': 'regularterm',
        'email': 'reg@example.com',
        'password': 'password123',
    })
    reg_token = resp.get_json()['token']
    client.put('/api/auth/accept-terms', headers={'Authorization': f'Bearer {reg_token}'})

    # Reset all
    resp = client.post('/api/admin/terms/reset', headers=headers)
    assert resp.status_code == 200

    # Check that regular user needs to re-accept
    resp = client.get('/api/auth/profile', headers={'Authorization': f'Bearer {reg_token}'})
    assert resp.get_json()['user']['terms_accepted'] is False
