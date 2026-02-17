"""Test configuration and fixtures"""

import pytest
from app import create_app, db
from app.models import User, Category


@pytest.fixture(scope='session')
def app():
    """Create application for testing"""
    app = create_app('testing')
    return app


@pytest.fixture(scope='function')
def db_session(app):
    """Create database session for a test"""
    with app.app_context():
        db.create_all()
        yield db
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app, db_session):
    """Create test client"""
    return app.test_client()


@pytest.fixture
def test_user(db_session):
    """Create a test user"""
    user = User(username='testuser', email='test@example.com')
    user.set_password('password123')
    db_session.session.add(user)
    db_session.session.commit()
    
    # Refresh to ensure user.id is loaded
    db_session.session.refresh(user)
    return user


@pytest.fixture
def test_user_2(db_session):
    """Create a second test user"""
    user = User(username='testuser2', email='test2@example.com')
    user.set_password('password456')
    db_session.session.add(user)
    db_session.session.commit()
    
    # Refresh to ensure user.id is loaded
    db_session.session.refresh(user)
    return user


@pytest.fixture
def auth_client(client, test_user):
    """Create authenticated test client"""
    with client:
        client.post('/auth/login', data={
            'email': test_user.email,
            'password': 'password123',
            'remember_me': False
        }, follow_redirects=True)
        yield client


@pytest.fixture
def test_category(db_session, test_user):
    """Create a test category"""
    category = Category(
        name='Work',
        description='Work related tasks',
        user_id=test_user.id,
        is_default=False
    )
    db_session.session.add(category)
    db_session.session.commit()
    
    db_session.session.refresh(category)
    return category
