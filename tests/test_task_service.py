"""Tests for task service functionality"""

import pytest
from datetime import datetime, timedelta
from app.services.task_service import TaskService
from app.exceptions import ValidationError, AuthorizationError, NotFoundError
from app.models import Task, User


class TestTaskService:
    """Test the TaskService class"""
    
    def test_create_task_success(self, db_session, test_user):
        """Test successful task creation"""
        task = TaskService.create_task(
            user_id=test_user.id,
            title="Test Task",
            description="Test description",
            due_date=None,
            category_id=None
        )
        
        assert task.id is not None
        assert task.title == "Test Task"
        assert task.description == "Test description"
        assert task.user_id == test_user.id
        assert task.status == 'todo'
        assert task.is_complete == False
    
    def test_create_task_with_category(self, db_session, test_user, test_category):
        """Test task creation with category"""
        task = TaskService.create_task(
            user_id=test_user.id,
            title="Work Task",
            description="Important work",
            due_date=None,
            category_id=test_category.id
        )
        
        assert task.category_id == test_category.id
        assert task.task_category.name == 'Work'
    
    def test_create_task_with_due_date(self, db_session, test_user):
        """Test task creation with due date"""
        due_date = datetime.utcnow() + timedelta(days=7)
        task = TaskService.create_task(
            user_id=test_user.id,
            title="Task with deadline",
            description="Must complete soon",
            due_date=due_date,
            category_id=None
        )
        
        assert task.due_date == due_date
    
    def test_create_task_short_title(self, test_user):
        """Test task creation with too short title"""
        with pytest.raises(ValidationError) as exc:
            TaskService.create_task(
                user_id=test_user.id,
                title="ab",
                description="Test",
                due_date=None,
                category_id=None
            )
        assert "at least 3 characters" in exc.value.message
    
    def test_create_task_empty_title(self, test_user):
        """Test task creation with empty title"""
        with pytest.raises(ValidationError) as exc:
            TaskService.create_task(
                user_id=test_user.id,
                title="",
                description="Test",
                due_date=None,
                category_id=None
            )
        assert "at least 3 characters" in exc.value.message
    
    def test_create_task_long_title(self, test_user):
        """Test task creation with too long title"""
        long_title = "a" * 101
        with pytest.raises(ValidationError) as exc:
            TaskService.create_task(
                user_id=test_user.id,
                title=long_title,
                description="Test",
                due_date=None,
                category_id=None
            )
        assert "must not exceed 100 characters" in exc.value.message
    
    def test_create_task_invalid_user(self, db_session):
        """Test task creation with invalid user ID"""
        with pytest.raises(NotFoundError):
            TaskService.create_task(
                user_id=99999,
                title="Test Task",
                description="Test",
                due_date=None,
                category_id=None
            )
    
    def test_update_task_status_success(self, db_session, test_user):
        """Test successful status update"""
        # Create task
        task = TaskService.create_task(
            user_id=test_user.id,
            title="Test Task",
            description="Test",
            due_date=None,
            category_id=None
        )
        
        # Update status
        updated_task = TaskService.update_task_status(
            task_id=task.id,
            user_id=test_user.id,
            new_status='doing'
        )
        
        assert updated_task.status == 'doing'
        assert updated_task.is_complete == False
        
        # Update to done
        completed_task = TaskService.update_task_status(
            task_id=task.id,
            user_id=test_user.id,
            new_status='done'
        )
        
        assert completed_task.status == 'done'
        assert completed_task.is_complete == True
    
    def test_update_task_status_unauthorized(self, db_session, test_user, test_user_2):
        """Test status update by unauthorized user"""
        # Create task as test_user
        task = TaskService.create_task(
            user_id=test_user.id,
            title="Test Task",
            description="Test",
            due_date=None,
            category_id=None
        )
        
        # Try to update as test_user_2
        with pytest.raises(AuthorizationError):
            TaskService.update_task_status(
                task_id=task.id,
                user_id=test_user_2.id,
                new_status='done'
            )
    
    def test_update_task_status_invalid(self, db_session, test_user):
        """Test status update with invalid status"""
        task = TaskService.create_task(
            user_id=test_user.id,
            title="Test Task",
            description="Test",
            due_date=None,
            category_id=None
        )
        
        with pytest.raises(ValidationError):
            TaskService.update_task_status(
                task_id=task.id,
                user_id=test_user.id,
                new_status='invalid_status'
            )
    
    def test_update_task_status_nonexistent_task(self, test_user):
        """Test updating non-existent task"""
        with pytest.raises(NotFoundError):
            TaskService.update_task_status(
                task_id=99999,
                user_id=test_user.id,
                new_status='done'
            )
    
    def test_get_user_tasks(self, db_session, test_user):
        """Test getting all tasks for a user"""
        # Create multiple tasks
        TaskService.create_task(test_user.id, "Task 1", "Desc 1")
        TaskService.create_task(test_user.id, "Task 2", "Desc 2")
        TaskService.create_task(test_user.id, "Task 3", "Desc 3")
        
        tasks = TaskService.get_user_tasks(test_user.id)
        assert len(tasks) == 3
    
    def test_get_user_tasks_filtered(self, db_session, test_user):
        """Test getting tasks filtered by status"""
        # Create tasks with different statuses
        task1 = TaskService.create_task(test_user.id, "Task 1", "Desc")
        task2 = TaskService.create_task(test_user.id, "Task 2", "Desc")
        task3 = TaskService.create_task(test_user.id, "Task 3", "Desc")
        
        TaskService.update_task_status(task2.id, test_user.id, 'doing')
        TaskService.update_task_status(task3.id, test_user.id, 'done')
        
        todo_tasks = TaskService.get_user_tasks(test_user.id, status='todo')
        doing_tasks = TaskService.get_user_tasks(test_user.id, status='doing')
        done_tasks = TaskService.get_user_tasks(test_user.id, status='done')
        
        assert len(todo_tasks) == 1
        assert len(doing_tasks) == 1
        assert len(done_tasks) == 1
    
    def test_delete_task_success(self, db_session, test_user):
        """Test successful task deletion"""
        task = TaskService.create_task(
            user_id=test_user.id,
            title="Task to delete",
            description="Will be deleted"
        )
        
        task_id = task.id
        TaskService.delete_task(task_id, test_user.id)
        
        # Verify task is deleted
        deleted_task = Task.query.get(task_id)
        assert deleted_task is None
    
    def test_delete_task_unauthorized(self, db_session, test_user, test_user_2):
        """Test deleting task by unauthorized user"""
        task = TaskService.create_task(
            user_id=test_user.id,
            title="Protected task",
            description="Cannot be deleted by others"
        )
        
        with pytest.raises(AuthorizationError):
            TaskService.delete_task(task.id, test_user_2.id)
    
    def test_delete_nonexistent_task(self, test_user):
        """Test deleting non-existent task"""
        with pytest.raises(NotFoundError):
            TaskService.delete_task(99999, test_user.id)
    
    def test_update_task_success(self, db_session, test_user):
        """Test successful task update"""
        task = TaskService.create_task(
            user_id=test_user.id,
            title="Original Title",
            description="Original description"
        )
        
        updated_task = TaskService.update_task(
            task_id=task.id,
            user_id=test_user.id,
            title="Updated Title",
            description="Updated description"
        )
        
        assert updated_task.title == "Updated Title"
        assert updated_task.description == "Updated description"
    
    def test_update_task_unauthorized(self, db_session, test_user, test_user_2):
        """Test updating task by unauthorized user"""
        task = TaskService.create_task(
            user_id=test_user.id,
            title="Protected task",
            description="Cannot be updated by others"
        )
        
        with pytest.raises(AuthorizationError):
            TaskService.update_task(
                task_id=task.id,
                user_id=test_user_2.id,
                title="Hacked title"
            )
    
    def test_update_task_invalid_title(self, db_session, test_user):
        """Test updating task with invalid title"""
        task = TaskService.create_task(
            user_id=test_user.id,
            title="Valid Title",
            description="Description"
        )
        
        with pytest.raises(ValidationError):
            TaskService.update_task(
                task_id=task.id,
                user_id=test_user.id,
                title="ab"  # Too short
            )
