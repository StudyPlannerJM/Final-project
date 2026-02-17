"""Tests for authentication functionality"""

from app.models import User


class TestUserModel:
    """Test the User model"""
    
    def test_password_hashing(self, db_session):
        """Test password hashing"""
        user = User(username='testuser', email='test@test.com')
        user.set_password('secret')
        
        assert user.password_hash != 'secret'
        assert user.check_password('secret')
        assert not user.check_password('wrong')
    
    def test_user_creation(self, db_session):
        """Test creating a user"""
        user = User(username='newuser', email='new@test.com')
        user.set_password('password')
        
        db_session.session.add(user)
        db_session.session.commit()
        
        saved_user = User.query.filter_by(username='newuser').first()
        assert saved_user is not None
        assert saved_user.email == 'new@test.com'
        assert saved_user.check_password('password')


class TestAuthRoutes:
    """Test authentication routes"""
    
    def test_login_page_loads(self, client):
        """Test that login page loads"""
        response = client.get('/auth/login')
        assert response.status_code == 200
        assert b'Sign In' in response.data or b'Login' in response.data
    
    def test_register_page_loads(self, client):
        """Test that register page loads"""
        response = client.get('/auth/register')
        assert response.status_code == 200
        assert b'Register' in response.data
    
    def test_successful_registration(self, client, db_session):
        """Test successful user registration"""
        response = client.post('/auth/register', data={
            'username': 'newuser',
            'email': 'newuser@test.com',
            'password': 'testpassword123',
            'password2': 'testpassword123'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        
        # Check user was created
        user = User.query.filter_by(email='newuser@test.com').first()
        assert user is not None
        assert user.username == 'newuser'
    
    def test_successful_login(self, client, test_user):
        """Test successful login"""
        response = client.post('/auth/login', data={
            'email': test_user.email,
            'password': 'password123',
            'remember_me': False
        }, follow_redirects=True)
        
        assert response.status_code == 200
        # Should redirect to dashboard after login
        assert b'Dashboard' in response.data or b'dashboard' in response.data
    
    def test_login_with_invalid_credentials(self, client, test_user):
        """Test login with wrong password"""
        response = client.post('/auth/login', data={
            'email': test_user.email,
            'password': 'wrongpassword',
            'remember_me': False
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'Invalid email or password' in response.data
    
    def test_login_with_nonexistent_user(self, client):
        """Test login with non-existent email"""
        response = client.post('/auth/login', data={
            'email': 'nonexistent@test.com',
            'password': 'password',
            'remember_me': False
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'Invalid email or password' in response.data
    
    def test_logout(self, auth_client):
        """Test logout functionality"""
        response = auth_client.get('/auth/logout', follow_redirects=True)
        
        assert response.status_code == 200
        assert b'logged out' in response.data or b'Sign In' in response.data
    
    def test_protected_route_requires_login(self, client):
        """Test that protected routes redirect to login"""
        response = client.get('/tasks')
        
        # Should redirect to login page
        assert response.status_code == 302
        assert '/auth/login' in response.location
    
    def test_authenticated_user_can_access_protected_route(self, auth_client):
        """Test that authenticated users can access protected routes"""
        response = auth_client.get('/tasks')
        
        assert response.status_code == 200
        assert b'Tasks' in response.data or b'task' in response.data
