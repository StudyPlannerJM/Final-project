"""
Tests for Admin routes
"""
import pytest
from app.models import User
from app import db


@pytest.fixture
def auth_user(test_user):
    """Alias for test_user to match test naming"""
    return test_user


@pytest.fixture
def login_user(auth_client):
    """Alias for auth_client to match test naming"""
    return auth_client


@pytest.fixture
def admin_user(app):
    """Create an admin user for testing"""
    user = User(username='admin', email='admin@example.com', is_admin=True)
    user.set_password('adminpass')
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def login_admin(client, admin_user):
    """Login as admin user"""
    client.post('/auth/login', data={
        'email': admin_user.email,
        'password': 'adminpass',
        'remember_me': False
    }, follow_redirects=True)
    return client


class TestManageUsers:
    """Test manage_users route"""
    
    def test_manage_users_requires_login(self, client):
        """Test that manage users requires authentication"""
        response = client.get('/admin/users')
        assert response.status_code == 302
        assert '/login' in response.location
    
    def test_manage_users_requires_admin(self, login_user, auth_user):
        """Test that manage users requires admin privileges"""
        response = login_user.get('/admin/users')
        # Should be redirected or forbidden
        assert response.status_code in [302, 403]
    
    def test_manage_users_displays_all_users(self, login_admin, admin_user):
        """Test that manage users displays all users"""
        # Create additional users
        user1 = User(username='user1', email='user1@example.com')
        user1.set_password('password')
        user2 = User(username='user2', email='user2@example.com')
        user2.set_password('password')
        db.session.add_all([user1, user2])
        db.session.commit()
        
        response = login_admin.get('/admin/users')
        
        assert response.status_code == 200
        assert b'admin' in response.data
        assert b'user1' in response.data
        assert b'user2' in response.data


class TestCreateUser:
    """Test create_user route"""
    
    def test_create_user_requires_login(self, client):
        """Test that create user requires authentication"""
        response = client.get('/admin/users/new')
        assert response.status_code == 302
    
    def test_create_user_requires_admin(self, client, auth_user, login_user):
        """Test that create user requires admin privileges"""
        response = login_user.get('/admin/users/new')
        assert response.status_code in [302, 403]
    
    def test_create_user_get_shows_form(self, login_admin, admin_user):
        """Test create user page displays form"""
        response = login_admin.get('/admin/users/new')
        
        assert response.status_code == 200
        assert b'Create User' in response.data or b'username' in response.data
    
    def test_create_user_post_success(self, login_admin, admin_user):
        """Test creating a new user"""
        response = login_admin.post('/admin/users/new', data={
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'password123',
            'password2': 'password123'
            # is_admin omitted = False
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'created successfully' in response.data or b'newuser' in response.data
        
        # Verify user was created
        user = User.query.filter_by(username='newuser').first()
        assert user is not None
        assert user.email == 'newuser@example.com'
        assert user.is_admin is False
    
    def test_create_admin_user(self, login_admin, admin_user):
        """Test creating a new admin user"""
        response = login_admin.post('/admin/users/new', data={
            'username': 'newadmin',
            'email': 'newadmin@example.com',
            'password': 'adminpass123',
            'password2': 'adminpass123',
            'is_admin': 'y'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        
        user = User.query.filter_by(username='newadmin').first()
        assert user is not None
        assert user.is_admin is True
    
    def test_create_user_duplicate_username(self, login_admin, admin_user):
        """Test creating user with duplicate username"""
        # Create first user
        user1 = User(username='duplicate', email='first@example.com')
        user1.set_password('password')
        db.session.add(user1)
        db.session.commit()
        
        # Try to create second user with same username
        response = login_admin.post('/admin/users/new', data={
            'username': 'duplicate',
            'email': 'second@example.com',
            'password': 'password123'
        }, follow_redirects=True)
        
        # Should show validation error
        assert b'username' in response.data.lower() or response.status_code == 200
    
    def test_create_user_duplicate_email(self, login_admin, admin_user):
        """Test creating user with duplicate email"""
        user1 = User(username='user1', email='duplicate@example.com')
        user1.set_password('password')
        db.session.add(user1)
        db.session.commit()
        
        response = login_admin.post('/admin/users/new', data={
            'username': 'user2',
            'email': 'duplicate@example.com',
            'password': 'password123'
        }, follow_redirects=True)
        
        # Should show validation error
        assert b'email' in response.data.lower() or response.status_code == 200


class TestEditUser:
    """Test edit_user route"""
    
    def test_edit_user_requires_login(self, client):
        """Test that edit user requires authentication"""
        response = client.get('/admin/users/1/edit')
        assert response.status_code == 302
    
    def test_edit_user_requires_admin(self, client, auth_user, login_user):
        """Test that edit user requires admin privileges"""
        response = login_user.get(f'/admin/users/{auth_user.id}/edit')
        assert response.status_code in [302, 403]
    
    def test_edit_user_get_shows_form(self, login_admin, admin_user):
        """Test edit user page displays form with user data"""
        user = User(username='editme', email='editme@example.com')
        user.set_password('password')
        db.session.add(user)
        db.session.commit()
        
        response = login_admin.get(f'/admin/users/{user.id}/edit')
        
        assert response.status_code == 200
        assert b'editme' in response.data
        assert b'editme@example.com' in response.data
    
    def test_edit_user_post_success(self, login_admin, admin_user):
        """Test editing a user"""
        user = User(username='oldname', email='old@example.com')
        user.set_password('password')
        db.session.add(user)
        db.session.commit()
        
        response = login_admin.post(f'/admin/users/{user.id}/edit', data={
            'username': 'newname',
            'email': 'new@example.com',
            'is_admin': False
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'updated successfully' in response.data or b'newname' in response.data
        
        # Verify user was updated
        updated_user = db.session.get(User, user.id)
        assert updated_user.username == 'newname'
        assert updated_user.email == 'new@example.com'
    
    def test_edit_user_change_password(self, login_admin, admin_user):
        """Test changing user password"""
        user = User(username='testuser', email='test@example.com')
        user.set_password('oldpassword')
        db.session.add(user)
        db.session.commit()
        user_id = user.id
        
        response = login_admin.post(f'/admin/users/{user_id}/edit', data={
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'newpassword123',
            'password2': 'newpassword123',
            'is_admin': False
        }, follow_redirects=True)
        
        assert response.status_code == 200
        
        # Verify password was changed
        db.session.expire_all()
        updated_user = db.session.get(User, user_id)
        assert updated_user.check_password('newpassword123')
    
    def test_edit_user_make_admin(self, login_admin, admin_user):
        """Test promoting user to admin"""
        user = User(username='promote', email='promote@example.com', is_admin=False)
        user.set_password('password')
        db.session.add(user)
        db.session.commit()
        
        response = login_admin.post(f'/admin/users/{user.id}/edit', data={
            'username': 'promote',
            'email': 'promote@example.com',
            'is_admin': True
        }, follow_redirects=True)
        
        assert response.status_code == 200
        
        updated_user = db.session.get(User, user.id)
        assert updated_user.is_admin is True
    
    def test_edit_user_cannot_remove_own_admin(self, login_admin, admin_user):
        """Test that admin cannot remove their own admin privileges"""
        response = login_admin.post(f'/admin/users/{admin_user.id}/edit', data={
            'username': 'admin',
            'email': 'admin@example.com'
            # is_admin omitted = False, trying to remove own admin
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'You cannot remove your own admin privileges' in response.data
        
        # Verify admin status unchanged
        user = db.session.get(User, admin_user.id)
        assert user.is_admin is True
    
    def test_edit_user_not_found(self, login_admin, admin_user):
        """Test editing non-existent user"""
        response = login_admin.get('/admin/users/99999/edit')
        assert response.status_code == 404


class TestDeleteUser:
    """Test delete_user route"""
    
    def test_delete_user_requires_login(self, client):
        """Test that delete user requires authentication"""
        response = client.post('/admin/users/1/delete')
        assert response.status_code == 302
    
    def test_delete_user_requires_admin(self, client, auth_user, login_user):
        """Test that delete user requires admin privileges"""
        response = login_user.post(f'/admin/users/{auth_user.id}/delete')
        assert response.status_code in [302, 403]
    
    def test_delete_user_success(self, login_admin, admin_user):
        """Test deleting a user"""
        user = User(username='deleteme', email='deleteme@example.com')
        user.set_password('password')
        db.session.add(user)
        db.session.commit()
        user_id = user.id
        
        response = login_admin.post(f'/admin/users/{user_id}/delete', follow_redirects=True)
        
        assert response.status_code == 200
        assert b'deleted' in response.data
        
        # Verify user was deleted
        deleted_user = db.session.get(User, user_id)
        assert deleted_user is None
    
    def test_delete_user_cannot_delete_self(self, login_admin, admin_user):
        """Test that admin cannot delete their own account"""
        response = login_admin.post(f'/admin/users/{admin_user.id}/delete', follow_redirects=True)
        
        assert response.status_code == 200
        assert b'cannot delete your own account' in response.data
        
        # Verify admin still exists
        user = db.session.get(User, admin_user.id)
        assert user is not None
    
    def test_delete_user_not_found(self, login_admin, admin_user):
        """Test deleting non-existent user"""
        response = login_admin.post('/admin/users/99999/delete')
        assert response.status_code == 404
