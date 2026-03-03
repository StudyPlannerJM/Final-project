"""
Tests for Tasks routes
"""
import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta
from app.models import Task, Category, User
from app import db


@pytest.fixture
def auth_user(test_user):
    """Alias for test_user to match test naming"""
    return test_user


@pytest.fixture
def login_user(auth_client):
    """Alias for auth_client to match test naming"""
    return auth_client


class TestTasksIndex:
    """Test tasks index route"""
    
    def test_index_requires_login(self, client):
        """Test that index requires authentication"""
        response = client.get('/tasks/')
        assert response.status_code == 302
        assert '/login' in response.location
    
    def test_index_displays_tasks_by_status(self, auth_client, test_user):
        """Test index displays tasks organized by status"""
        # Create tasks with different statuses
        todo_task = Task(
            title='Todo Task',
            user_id=test_user.id,
            status='todo'
        )
        doing_task = Task(
            title='Doing Task',
            user_id=test_user.id,
            status='doing'
        )
        done_task = Task(
            title='Done Task',
            user_id=test_user.id,
            status='done'
        )
        db.session.add_all([todo_task, doing_task, done_task])
        db.session.commit()
        
        response = auth_client.get('/tasks/')
        
        assert response.status_code == 200
        assert b'Todo Task' in response.data
        assert b'Doing Task' in response.data
        assert b'Done Task' in response.data
    
    def test_index_only_shows_user_tasks(self, login_user, auth_user):
        """Test index only shows current user's tasks"""
        # Create another user
        other_user = User(username='otheruser', email='other@example.com')
        other_user.set_password('password123')
        db.session.add(other_user)
        db.session.flush()
        
        # Create task for other user
        other_task = Task(
            title='Other User Task',
            user_id=other_user.id,
            status='todo'
        )
        my_task = Task(
            title='My Task',
            user_id=auth_user.id,
            status='todo'
        )
        db.session.add_all([other_task, my_task])
        db.session.commit()
        
        response = login_user.get('/tasks/')
        
        assert b'My Task' in response.data
        assert b'Other User Task' not in response.data


class TestUpdateStatus:
    """Test update_status route (AJAX endpoint)"""
    
    def test_update_status_requires_login(self, client):
        """Test that update_status requires authentication"""
        response = client.post('/tasks/update_status/1/doing')
        assert response.status_code == 302
    
    def test_update_status_success(self, login_user, auth_user):
        """Test successful status update"""
        task = Task(
            title='Test Task',
            user_id=auth_user.id,
            status='todo'
        )
        db.session.add(task)
        db.session.commit()
        
        response = login_user.post(f'/tasks/update_status/{task.id}/doing')
        
        assert response.status_code == 200
        json_data = response.get_json()
        assert json_data['success'] is True
        assert json_data['new_status'] == 'doing'
        
        # Verify database was updated
        updated_task = db.session.get(Task, task.id)
        assert updated_task.status == 'doing'
    
    def test_update_status_invalid_status(self, login_user, auth_user):
        """Test update with invalid status"""
        task = Task(
            title='Test Task',
            user_id=auth_user.id,
            status='todo'
        )
        db.session.add(task)
        db.session.commit()
        
        response = login_user.post(f'/tasks/update_status/{task.id}/invalid')
        
        assert response.status_code == 400
        json_data = response.get_json()
        assert json_data['success'] is False
    
    def test_update_status_unauthorized(self, login_user, auth_user):
        """Test update of another user's task"""
        other_user = User(username='otheruser', email='other@example.com')
        other_user.set_password('password123')
        db.session.add(other_user)
        db.session.flush()
        
        task = Task(
            title='Other Task',
            user_id=other_user.id,
            status='todo'
        )
        db.session.add(task)
        db.session.commit()
        
        response = login_user.post(f'/tasks/update_status/{task.id}/doing')
        
        # Should be forbidden or redirect
        assert response.status_code in [302, 403]


class TestAddTask:
    """Test add task route"""
    
    def test_add_task_get_requires_login(self, client):
        """Test that add task page requires authentication"""
        response = client.get('/tasks/add')
        assert response.status_code == 302
        assert '/login' in response.location
    
    def test_add_task_get_shows_form(self, login_user, auth_user):
        """Test add task page displays form"""
        response = login_user.get('/tasks/add')
        
        assert response.status_code == 200
        assert b'Add New Task' in response.data or b'title' in response.data
    
    def test_add_task_post_creates_task(self, login_user, auth_user):
        """Test creating a new task"""
        response = login_user.post('/tasks/add', data={
            'title': 'New Test Task',
            'description': 'This is a test description',
            'category': ''
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'Task added successfully!' in response.data or b'New Test Task' in response.data
        
        # Verify task was created
        task = Task.query.filter_by(title='New Test Task').first()
        assert task is not None
        assert task.user_id == auth_user.id
        assert task.description == 'This is a test description'
    
    def test_add_task_with_category(self, login_user, auth_user):
        """Test creating task with predefined category"""
        category = Category(name='Work', user_id=auth_user.id, is_default=True)
        db.session.add(category)
        db.session.commit()
        
        response = login_user.post('/tasks/add', data={
            'title': 'Work Task',
            'category': category.id
        }, follow_redirects=True)
        
        assert response.status_code == 200
        
        task = Task.query.filter_by(title='Work Task').first()
        assert task is not None
        assert task.category_id == category.id
    
    def test_add_task_with_custom_category(self, login_user, auth_user):
        """Test creating task with custom category"""
        response = login_user.post('/tasks/add', data={
            'title': 'Custom Category Task',
            'other_category': 'My Custom Category'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        
        task = Task.query.filter_by(title='Custom Category Task').first()
        assert task is not None
        
        category = db.session.get(Category, task.category_id)
        assert category is not None
        assert category.name == 'My Custom Category'
        assert category.user_id == auth_user.id
        assert category.is_default is False
    
    def test_add_task_with_due_date(self, login_user, auth_user):
        """Test creating task with due date"""
        due_date = datetime.now() + timedelta(days=7)
        
        response = login_user.post('/tasks/add', data={
            'title': 'Task with Due Date',
            'due_date': due_date.strftime('%Y-%m-%dT%H:%M')
        }, follow_redirects=True)
        
        assert response.status_code == 200
        
        task = Task.query.filter_by(title='Task with Due Date').first()
        assert task is not None
        assert task.due_date is not None
    
    @patch('app.routes.tasks.get_calendar_service')
    @patch('app.routes.tasks.create_calendar_event')
    def test_add_task_syncs_to_calendar(self, mock_create, mock_service, client, auth_user, login_user):
        """Test task syncs to Google Calendar when enabled"""
        auth_user.calendar_sync_enabled = True
        db.session.commit()
        
        mock_service.return_value = Mock()
        mock_create.return_value = 'event_id_123'
        
        due_date = datetime.now() + timedelta(days=1)
        
        response = login_user.post('/tasks/add', data={
            'title': 'Calendar Task',
            'due_date': due_date.strftime('%Y-%m-%dT%H:%M')
        }, follow_redirects=True)
        
        assert response.status_code == 200
        
        task = Task.query.filter_by(title='Calendar Task').first()
        assert task is not None
        assert task.google_event_id == 'event_id_123'
        assert task.synced_to_calendar is True


class TestEditTask:
    """Test edit task route"""
    
    def test_edit_task_requires_login(self, client):
        """Test that edit task requires authentication"""
        response = client.get('/tasks/edit/1')
        assert response.status_code == 302
    
    def test_edit_task_get_shows_form(self, login_user, auth_user):
        """Test edit page displays form with task data"""
        task = Task(
            title='Original Title',
            description='Original Description',
            user_id=auth_user.id
        )
        db.session.add(task)
        db.session.commit()
        
        response = login_user.get(f'/tasks/edit/{task.id}')
        
        assert response.status_code == 200
        assert b'Original Title' in response.data
    
    def test_edit_task_post_updates_task(self, login_user, auth_user):
        """Test updating a task"""
        task = Task(
            title='Original Title',
            user_id=auth_user.id
        )
        db.session.add(task)
        db.session.commit()
        
        response = login_user.post(f'/tasks/edit/{task.id}', data={
            'title': 'Updated Title',
            'description': 'Updated Description'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'updated' in response.data.lower()
        
        updated_task = db.session.get(Task, task.id)
        assert updated_task.title == 'Updated Title'
        assert updated_task.description == 'Updated Description'
    
    def test_edit_task_changes_category(self, login_user, auth_user):
        """Test changing task category"""
        old_category = Category(name='Old', user_id=auth_user.id)
        new_category = Category(name='New', user_id=auth_user.id)
        db.session.add_all([old_category, new_category])
        db.session.flush()
        
        task = Task(
            title='Task',
            user_id=auth_user.id,
            category_id=old_category.id
        )
        db.session.add(task)
        db.session.commit()
        
        response = login_user.post(f'/tasks/edit/{task.id}', data={
            'title': 'Task',
            'category': new_category.id
        }, follow_redirects=True)
        
        assert response.status_code == 200
        
        updated_task = db.session.get(Task, task.id)
        assert updated_task.category_id == new_category.id
    
    def test_edit_task_unauthorized(self, login_user, auth_user):
        """Test editing another user's task"""
        other_user = User(username='otheruser', email='other@example.com')
        other_user.set_password('password123')
        db.session.add(other_user)
        db.session.flush()
        
        task = Task(
            title='Other Task',
            user_id=other_user.id
        )
        db.session.add(task)
        db.session.commit()
        
        response = login_user.get(f'/tasks/edit/{task.id}')
        
        assert response.status_code in [302, 403]
    
    @patch('app.routes.tasks.get_calendar_service')
    @patch('app.routes.tasks.update_calendar_event')
    def test_edit_task_updates_calendar(self, mock_update, mock_service, client, auth_user, login_user):
        """Test editing task updates Google Calendar"""
        auth_user.calendar_sync_enabled = True
        db.session.commit()
        
        task = Task(
            title='Calendar Task',
            user_id=auth_user.id,
            google_event_id='event_123'
        )
        db.session.add(task)
        db.session.commit()
        
        mock_service.return_value = Mock()
        
        response = login_user.post(f'/tasks/edit/{task.id}', data={
            'title': 'Updated Calendar Task'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert mock_update.called


class TestDeleteTask:
    """Test delete task route"""
    
    def test_delete_task_requires_login(self, client):
        """Test that delete requires authentication"""
        response = client.post('/tasks/delete/1')
        assert response.status_code == 302
    
    def test_delete_task_success(self, login_user, auth_user):
        """Test successful task deletion"""
        task = Task(
            title='Task to Delete',
            user_id=auth_user.id
        )
        db.session.add(task)
        db.session.commit()
        task_id = task.id
        
        response = login_user.post(f'/tasks/delete/{task_id}', follow_redirects=True)
        
        assert response.status_code == 200
        assert b'deleted' in response.data.lower()
        
        # Verify task was deleted
        deleted_task = db.session.get(Task, task_id)
        assert deleted_task is None
    
    def test_delete_task_unauthorized(self, login_user, auth_user):
        """Test deleting another user's task"""
        other_user = User(username='otheruser', email='other@example.com')
        other_user.set_password('password123')
        db.session.add(other_user)
        db.session.flush()
        
        task = Task(
            title='Other Task',
            user_id=other_user.id
        )
        db.session.add(task)
        db.session.commit()
        
        response = login_user.post(f'/tasks/delete/{task.id}')
        
        assert response.status_code in [302, 403]
    
    @patch('app.routes.tasks.get_calendar_service')
    @patch('app.routes.tasks.delete_calendar_event')
    def test_delete_task_removes_from_calendar(self, mock_delete, mock_service, client, auth_user, login_user):
        """Test deleting task removes from Google Calendar"""
        auth_user.calendar_sync_enabled = True
        db.session.commit()
        
        task = Task(
            title='Calendar Task',
            user_id=auth_user.id,
            google_event_id='event_123'
        )
        db.session.add(task)
        db.session.commit()
        
        mock_service.return_value = Mock()
        
        response = login_user.post(f'/tasks/delete/{task.id}', follow_redirects=True)
        
        assert response.status_code == 200
        assert mock_delete.called


class TestCompleteTask:
    """Test complete task route"""
    
    def test_complete_task_requires_login(self, client):
        """Test that complete requires authentication"""
        response = client.post('/tasks/complete/1')
        assert response.status_code == 302
    
    def test_complete_task_toggles_status(self, login_user, auth_user):
        """Test completing a task"""
        task = Task(
            title='Task to Complete',
            user_id=auth_user.id,
            is_complete=False
        )
        db.session.add(task)
        db.session.commit()
        
        response = login_user.post(f'/tasks/complete/{task.id}', follow_redirects=True)
        
        assert response.status_code == 200
        
        updated_task = db.session.get(Task, task.id)
        assert updated_task.is_complete is True
    
    def test_complete_task_toggles_back(self, login_user, auth_user):
        """Test uncompleting a task"""
        task = Task(
            title='Completed Task',
            user_id=auth_user.id,
            is_complete=True
        )
        db.session.add(task)
        db.session.commit()
        
        response = login_user.post(f'/tasks/complete/{task.id}', follow_redirects=True)
        
        assert response.status_code == 200
        
        updated_task = db.session.get(Task, task.id)
        assert updated_task.is_complete is False
    
    def test_complete_task_unauthorized(self, login_user, auth_user):
        """Test completing another user's task"""
        other_user = User(username='otheruser', email='other@example.com')
        other_user.set_password('password123')
        db.session.add(other_user)
        db.session.flush()
        
        task = Task(
            title='Other Task',
            user_id=other_user.id
        )
        db.session.add(task)
        db.session.commit()
        
        response = login_user.post(f'/tasks/complete/{task.id}')
        
        assert response.status_code in [302, 403]
