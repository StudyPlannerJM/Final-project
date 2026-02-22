"""
Pomodoro service for business logic related to pomodoro sessions
"""

from datetime import datetime, timedelta
from app import db
from app.models import PomodoroSession, StudySession, Task, User
from app.exceptions import (
    ValidationError, AuthorizationError, NotFoundError
)


class PomodoroService:
    """Service class for pomodoro session operations"""
    
    @staticmethod
    def create_session(user_id, duration, task_id=None, completed=True):
        """
        Create a new pomodoro session with corresponding study session.
        
        Args:
            user_id: ID of the user creating the session
            duration: Duration in minutes (default: 25)
            task_id: Optional task ID to link
            completed: Whether the session was completed (default: True)
            
        Returns:
            Tuple of (PomodoroSession, total_minutes_today)
            
        Raises:
            ValidationError: If validation fails
            NotFoundError: If user or task not found
        """
        # Validate user exists
        user = User.query.get(user_id)
        if not user:
            raise NotFoundError(f"User with id {user_id} not found")
        
        # Validate duration
        if duration <= 0 or duration > 120:
            raise ValidationError("Duration must be between 1 and 120 minutes")
        
        # If task_id provided, validate it exists and belongs to user
        if task_id:
            task = Task.query.get(task_id)
            if not task:
                raise NotFoundError(f"Task with id {task_id} not found")
            if task.user_id != user_id:
                raise AuthorizationError("You don't have permission to link this task")
        
        # Calculate start and end times
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(minutes=duration)
        
        # Create Pomodoro session
        pomodoro = PomodoroSession(
            user_id=user_id,
            task_id=task_id if task_id else None,
            duration_minutes=duration,
            break_duration_minutes=5,
            start_time=start_time,
            end_time=end_time,
            completed=completed
        )
        db.session.add(pomodoro)

        # Create corresponding study session
        study_session = StudySession(
            user_id=user_id,
            task_id=task_id if task_id else None,
            start_time=start_time,
            end_time=end_time,
            duration_minutes=duration
        )
        db.session.add(study_session)
        db.session.flush()  # Get IDs

        # Link them
        pomodoro.study_session_id = study_session.id

        # Update task's actual time
        if task_id:
            task = Task.query.get(task_id)
            if task and task.user_id == user_id:
                task.actual_minutes = (task.actual_minutes or 0) + duration

        db.session.commit()
        
        # Get today's total minutes
        total_minutes_today = PomodoroService.get_today_study_minutes(user_id)
        
        return pomodoro, total_minutes_today
    
    @staticmethod
    def delete_session(session_id, user_id):
        """
        Delete a pomodoro session.
        
        Args:
            session_id: ID of the session to delete
            user_id: ID of the user making the deletion
            
        Raises:
            NotFoundError: If session not found
            AuthorizationError: If user doesn't own the session
        """
        session = PomodoroSession.query.get(session_id)
        if not session:
            raise NotFoundError(f"Session with id {session_id} not found")
        
        if session.user_id != user_id:
            raise AuthorizationError("You don't have permission to delete this session")
        
        db.session.delete(session)
        db.session.commit()
    
    @staticmethod
    def get_user_statistics(user_id):
        """
        Calculate statistics for a user's pomodoro sessions.
        
        Args:
            user_id: ID of the user
            
        Returns:
            Dictionary with total_sessions, completed_sessions, total_minutes
            
        Raises:
            NotFoundError: If user not found
        """
        user = User.query.get(user_id)
        if not user:
            raise NotFoundError(f"User with id {user_id} not found")
        
        all_sessions = PomodoroSession.query.filter_by(user_id=user_id).all()
        total_sessions = len(all_sessions)
        completed_sessions = len([s for s in all_sessions if s.completed])
        total_minutes = sum([s.duration_minutes for s in all_sessions if s.completed])
        
        return {
            'total_sessions': total_sessions,
            'completed_sessions': completed_sessions,
            'total_minutes': total_minutes
        }
    
    @staticmethod
    def get_today_study_minutes(user_id):
        """
        Get total study minutes for today.
        
        Args:
            user_id: ID of the user
            
        Returns:
            Total minutes studied today
        """
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

        total = db.session.query(db.func.sum(StudySession.duration_minutes)).filter(
            StudySession.user_id == user_id,
            StudySession.start_time >= today_start
        ).scalar()

        return total or 0
