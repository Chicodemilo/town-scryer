import pytest
from app import create_app, db as _db


@pytest.fixture(scope='session')
def app():
    """Create an application instance for tests."""
    app = create_app(test_config={
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'SECRET_KEY': 'test-secret-key',
    })

    with app.app_context():
        _db.create_all()
        yield app
        _db.session.remove()
        _db.drop_all()


@pytest.fixture(scope='function')
def db(app):
    """Provide a clean database for each test."""
    with app.app_context():
        yield _db
        _db.session.rollback()
        # Delete all data from all tables to ensure test isolation
        for table in reversed(_db.metadata.sorted_tables):
            _db.session.execute(table.delete())
        _db.session.commit()


@pytest.fixture()
def client(app):
    """Flask test client."""
    return app.test_client()


@pytest.fixture()
def auth_headers(client):
    """Register a test user and return auth headers."""
    client.post('/api/auth/register', json={
        'username': 'testuser',
        'email': 'test@example.com',
        'password': 'password123',
    })
    resp = client.post('/api/auth/login', json={
        'username': 'testuser',
        'password': 'password123',
    })
    token = resp.get_json()['token']
    return {'Authorization': f'Bearer {token}'}
