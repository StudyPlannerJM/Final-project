"""Task service for business logic related to tasks"""

from app import db
from app.models import Task, User
from app.exceptions import (
    ValidationError, AuthorizationError, NotFoundError
)


class TaskService:
    """Service class for task operations"""
    
    @staticmethod
    def create_task(
        user_id, title, description, due_date=None, category_id=None
    ):
        """
        Create a new task with validation.
        
        Args:
            user_id: ID of the user creating the task
            title: Task title
            description: Task description
            due_date: Optional due date
            category_id: Optional category ID
            
        Returns:
            Created Task object
            
        Raises:
            ValidationError: If validation fails
        """
        # Validate title
        if not title or len(title.strip()) < 3:
            raise ValidationError(
                "Task title must be at least 3 characters long"
            )
        
        if len(title) > 100:
            raise ValidationError(
                "Task title must not exceed 100 characters"
            )
        
        # Validate user exists
        user = db.session.get(User, user_id)
        if not user:
            raise NotFoundError(f"User with id {user_id} not found")
        
        # Create task
        task = Task(
            title=title.strip(),
            description=description.strip() if description else "",
            due_date=due_date,
            category_id=category_id,
            user_id=user_id,
            status='todo'
        )
        
        db.session.add(task)
        db.session.commit()
        
        return task
    
    @staticmethod
    def update_task_status(task_id, user_id, new_status):
        """
        Update the status of a task.
        
        Args:
            task_id: ID of the task to update
            user_id: ID of the user making the update
            new_status: New status ('todo', 'doing', or 'done')
            
        Returns:
            Updated Task object
            
        Raises:
            NotFoundError: If task not found
            AuthorizationError: If user doesn't own the task
            ValidationError: If status is invalid
        """
        # Get task
        task = db.session.get(Task, task_id)
        if not task:
            raise NotFoundError(f"Task with id {task_id} not found")
        
        # Check authorization
        if task.user_id != user_id:
            raise AuthorizationError(
                "You are not authorized to update this task"
            )
        
        # Validate status
        valid_statuses = ['todo', 'doing', 'done']
        if new_status not in valid_statuses:
            raise ValidationError(
                f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
            )
        
        # Update task
        task.status = new_status
        if new_status == 'done':
            task.is_complete = True
        else:
            task.is_complete = False
            
        db.session.commit()
        
        return task
    
    @staticmethod
    def get_user_tasks(user_id, status=None):
        """
        Get all tasks for a user, optionally filtered by status.
        
        Args:
            user_id: ID of the user
            status: Optional status filter
            
        Returns:
            List of Task objects
        """
        query = Task.query.filter_by(user_id=user_id)
        
        if status:
            query = query.filter_by(status=status)
        
        return query.order_by(Task.date_created.desc()).all()
    
    @staticmethod
    def delete_task(task_id, user_id):
        """
        Delete a task.
        
        Args:
            task_id: ID of the task to delete
            user_id: ID of the user making the deletion
            
        Raises:
            NotFoundError: If task not found
            AuthorizationError: If user doesn't own the task
        """
        task = db.session.get(Task, task_id)
        if not task:
            raise NotFoundError(f"Task with id {task_id} not found")
        
        if task.user_id != user_id:
            raise AuthorizationError(
                "You are not authorized to delete this task"
            )
        
        db.session.delete(task)
        db.session.commit()
    
    @staticmethod
    def update_task(task_id, user_id, **kwargs):
        """
        Update task fields.
        
        Args:
            task_id: ID of the task to update
            user_id: ID of the user making the update
            **kwargs: Fields to update
                (title, description, due_date, category_id)
            
        Returns:
            Updated Task object
            
        Raises:
            NotFoundError: If task not found
            AuthorizationError: If user doesn't own the task
            ValidationError: If validation fails
        """
        task = db.session.get(Task, task_id)
        if not task:
            raise NotFoundError(f"Task with id {task_id} not found")
        
        if task.user_id != user_id:
            raise AuthorizationError(
                "You are not authorized to update this task"
            )
        
        # Update allowed fields
        if 'title' in kwargs:
            title = kwargs['title']
            if not title or len(title.strip()) < 3:
                raise ValidationError(
                    "Task title must be at least 3 characters long"
                )
            if len(title) > 100:
                raise ValidationError(
                    "Task title must not exceed 100 characters"
                )
            task.title = title.strip()
        
        if 'description' in kwargs:
            desc = kwargs['description']
            task.description = desc.strip() if desc else ""
        
        if 'due_date' in kwargs:
            task.due_date = kwargs['due_date']
        
        if 'category_id' in kwargs:
            task.category_id = kwargs['category_id']
        
        if 'status' in kwargs:
            status = kwargs['status']
            valid_statuses = ['todo', 'doing', 'done']
            if status not in valid_statuses:
                raise ValidationError(
                    f"Invalid status. Must be one of: "
                    f"{', '.join(valid_statuses)}"
                )
            task.status = status
            task.is_complete = (status == 'done')
        
        db.session.commit()
        
        return task
