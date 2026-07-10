import pytest


def test_register(client, db):
    resp = client.post('/api/auth/register', json={
        'username': 'newuser',
        'email': 'new@example.com',
        'password': 'password123',
    })
    assert resp.status_code == 201
    data = resp.get_json()
    assert 'token' in data
    assert data['user']['username'] == 'newuser'


def test_register_duplicate(client, db):
    client.post('/api/auth/register', json={
        'username': 'dup',
        'email': 'dup@example.com',
        'password': 'password123',
    })
    resp = client.post('/api/auth/register', json={
        'username': 'dup',
        'email': 'dup2@example.com',
        'password': 'password123',
    })
    assert resp.status_code == 409


def test_login_success(client, db):
    client.post('/api/auth/register', json={
        'username': 'loginuser',
        'email': 'login@example.com',
        'password': 'password123',
    })
    resp = client.post('/api/auth/login', json={
        'username': 'loginuser',
        'password': 'password123',
    })
    assert resp.status_code == 200
    assert 'token' in resp.get_json()


def test_login_wrong_password(client, db):
    client.post('/api/auth/register', json={
        'username': 'wpuser',
        'email': 'wp@example.com',
        'password': 'password123',
    })
    resp = client.post('/api/auth/login', json={
        'username': 'wpuser',
        'password': 'wrong',
    })
    assert resp.status_code == 401


def test_login_missing_fields(client):
    resp = client.post('/api/auth/login', json={})
    assert resp.status_code in (400, 401)


def test_protected_route_without_token(client):
    resp = client.get('/api/auth/profile')
    assert resp.status_code == 401


