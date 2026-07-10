import pytest


def test_change_email(client, db):
    resp = client.post('/api/auth/register', json={
        'username': 'emailuser',
        'email': 'old@example.com',
        'password': 'password123',
    })
    token = resp.get_json()['token']
    headers = {'Authorization': f'Bearer {token}'}

    # Request email change
    resp = client.put('/api/auth/change-email', json={'email': 'new@example.com'}, headers=headers)
    assert resp.status_code == 200
    assert resp.get_json()['user']['pending_email'] == 'new@example.com'

    # Old email should still be current
    resp = client.get('/api/auth/profile', headers=headers)
    assert resp.get_json()['user']['email'] == 'old@example.com'


def test_change_email_same(client, db):
    resp = client.post('/api/auth/register', json={
        'username': 'sameuser',
        'email': 'same@example.com',
        'password': 'password123',
    })
    token = resp.get_json()['token']
    headers = {'Authorization': f'Bearer {token}'}

    resp = client.put('/api/auth/change-email', json={'email': 'same@example.com'}, headers=headers)
    assert resp.status_code == 400


def test_change_email_taken(client, db):
    client.post('/api/auth/register', json={
        'username': 'user1ec',
        'email': 'taken@example.com',
        'password': 'password123',
    })
    resp = client.post('/api/auth/register', json={
        'username': 'user2ec',
        'email': 'other@example.com',
        'password': 'password123',
    })
    token = resp.get_json()['token']
    headers = {'Authorization': f'Bearer {token}'}

    resp = client.put('/api/auth/change-email', json={'email': 'taken@example.com'}, headers=headers)
    assert resp.status_code == 400


def test_verify_new_email(client, db):
    resp = client.post('/api/auth/register', json={
        'username': 'verifychange',
        'email': 'before@example.com',
        'password': 'password123',
    })
    token = resp.get_json()['token']
    headers = {'Authorization': f'Bearer {token}'}

    # Request change
    client.put('/api/auth/change-email', json={'email': 'after@example.com'}, headers=headers)

    # Get the pending email token from DB
    from app.models.user import User
    user = User.query.filter_by(username='verifychange').first()
    email_token = user.pending_email_token

    # Verify the new email
    resp = client.get(f'/api/auth/verify-new-email?token={email_token}')
    assert resp.status_code == 200

    # Confirm email changed
    resp = client.get('/api/auth/profile', headers=headers)
    assert resp.get_json()['user']['email'] == 'after@example.com'
    assert resp.get_json()['user']['pending_email'] is None
