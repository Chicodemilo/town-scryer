import pytest
from app.models.user import User


def test_register_creates_unverified_user(client, db):
    resp = client.post('/api/auth/register', json={
        'username': 'verifyuser',
        'email': 'verify@example.com',
        'password': 'password123',
    })
    assert resp.status_code == 201
    data = resp.get_json()
    assert data['user']['email_verified'] is False


def test_verify_email_with_valid_token(client, db):
    client.post('/api/auth/register', json={
        'username': 'verifyuser2',
        'email': 'verify2@example.com',
        'password': 'password123',
    })
    user = User.query.filter_by(username='verifyuser2').first()
    token = user.verification_token
    assert token is not None

    resp = client.get(f'/api/auth/verify-email?token={token}')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['user']['email_verified'] is True


def test_verify_email_with_invalid_token(client, db):
    resp = client.get('/api/auth/verify-email?token=invalid-token')
    assert resp.status_code == 400


def test_verify_email_missing_token(client, db):
    resp = client.get('/api/auth/verify-email')
    assert resp.status_code == 400


def test_resend_verification(client, db):
    resp = client.post('/api/auth/register', json={
        'username': 'resenduser',
        'email': 'resend@example.com',
        'password': 'password123',
    })
    token = resp.get_json()['token']

    resp = client.post('/api/auth/resend-verification',
                       headers={'Authorization': f'Bearer {token}'})
    assert resp.status_code == 200


def test_resend_verification_already_verified(client, db):
    resp = client.post('/api/auth/register', json={
        'username': 'alreadyverified',
        'email': 'already@example.com',
        'password': 'password123',
    })
    auth_token = resp.get_json()['token']
    user = User.query.filter_by(username='alreadyverified').first()

    # Manually verify
    user.email_verified = True
    db.session.commit()

    resp = client.post('/api/auth/resend-verification',
                       headers={'Authorization': f'Bearer {auth_token}'})
    assert resp.status_code == 400
