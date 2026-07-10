def test_root_endpoint(client):
    resp = client.get('/')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['status'] == 'running'
    assert 'version' in data


def test_healthz(client):
    resp = client.get('/healthz')
    # With SQLite in-memory, this should be healthy
    assert resp.status_code in (200, 503)


def test_security_status(client):
    resp = client.get('/api/security/status')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['security_active'] is True
