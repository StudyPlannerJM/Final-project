"""
Calendar service for business logic related to Google Calendar integration
"""

import json
from datetime import datetime, timedelta
from calendar import monthrange
from app import db
from app.models import Task, User
from app.exceptions import (
    ValidationError, AuthorizationError, NotFoundError
)
from app.utils.calendar_client import (
    get_calendar_service,
    sync_unsynced_tasks_to_calendar,
    get_events_for_date_range,
    create_calendar_event,
    update_calendar_event,
    delete_calendar_event
)


class CalendarService:
    """Service class for Google Calendar operations"""
    
    @staticmethod
    def connect_google_calendar(user, credentials):
        """
        Save Google Calendar credentials to user account.
        
        Args:
            user: User object
            credentials: Google OAuth credentials object
            
        Returns:
            Number of unsynced tasks that could be synced
        """
        # Save credentials to database as JSON
        token_data = {
            'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': credentials.scopes
        }

        user.google_token = json.dumps(token_data)
        user.calendar_sync_enabled = True
        db.session.commit()
        
        # Count unsynced tasks
        unsynced_count = Task.query.filter_by(
            user_id=user.id,
            synced_to_calendar=False
        ).filter(Task.due_date.isnot(None)).count()
        
        return unsynced_count
    
    @staticmethod
    def disconnect_google_calendar(user_id):
        """
        Remove Google Calendar connection.
        
        Args:
            user_id: ID of the user
            
        Raises:
            NotFoundError: If user not found
        """
        user = db.session.get(User, user_id)
        if not user:
            raise NotFoundError(f"User with id {user_id} not found")
        
        user.google_token = None
        user.calendar_sync_enabled = False
        db.session.commit()
    
    @staticmethod
    def sync_existing_tasks(user):
        """
        Sync all existing unsynced tasks to Google Calendar.
        
        Args:
            user: User object
            
        Returns:
            Tuple of (success_count, total_count)
            
        Raises:
            ValidationError: If calendar not connected
        """
        if not user.calendar_sync_enabled:
            raise ValidationError("Google Calendar not connected")
        
        success_count, total_count = sync_unsynced_tasks_to_calendar(user)
        return success_count, total_count
    
    @staticmethod
    def get_calendar_events(user, start_date, end_date, view='week'):
        """
        Get calendar events and tasks for a date range.
        
        Args:
            user: User object
            start_date: Start datetime
            end_date: End datetime
            view: View type ('week', 'month', 'day')
            
        Returns:
            Dictionary with calendar_events, tasks, calendar_connected, week_dates
        """
        # Fetch Google Calendar events (if connected)
        calendar_events = []
        calendar_connected = False
        
        if user.calendar_sync_enabled and user.google_token:
            service = get_calendar_service(user)
            if service:
                try:
                    calendar_events = get_events_for_date_range(service, start_date, end_date)
                    calendar_connected = True
                except Exception as e:
                    print(f"Error fetching calendar events: {e}")
                    calendar_connected = False

        # Fetch local tasks for the date range
        tasks = Task.query.filter(
            Task.user_id == user.id,
            Task.due_date.isnot(None),
            Task.due_date >= start_date,
            Task.due_date <= end_date
        ).order_by(Task.due_date.asc()).all()

        # Filter out duplicate Google Calendar events (tasks already synced)
        synced_event_ids = [task.google_event_id for task in tasks if task.google_event_id]
        calendar_events = [e for e in calendar_events if e.get('id') not in synced_event_ids]

        # Format tasks as JSON
        tasks_json = []
        for task in tasks:
            tasks_json.append({
                'id': task.id,
                'title': task.title,
                'description': task.description,
                'due_date': task.due_date.isoformat(),
                'status': task.status,
                'category': {
                    'name': task.task_category.name if task.task_category else None,
                    'color': task.task_category.color if task.task_category else '#3498db',
                    'icon': task.task_category.icon if task.task_category else None
                } if task.task_category else None,
                'synced': task.synced_to_calendar
            })

        # Calculate week dates for week view
        week_dates = []
        if view == 'week':
            # Get the start of the week (Monday)
            start_of_week = start_date
            for i in range(7):
                day = start_of_week + timedelta(days=i)
                week_dates.append({
                    'date': day.strftime('%Y-%m-%d'),
                    'day_name': day.strftime('%A'),
                    'day_num': day.day,
                    'is_today': day.date() == datetime.now().date()
                })

        return {
            'calendar_connected': calendar_connected,
            'calendar_events': calendar_events,
            'tasks': tasks_json,
            'week_dates': week_dates
        }
    
    @staticmethod
    def calculate_date_range(target_date, view):
        """
        Calculate start and end dates for a given view type.
        
        Args:
            target_date: Target datetime
            view: View type ('week', 'month', 'day', 'upcoming')
            
        Returns:
            Tuple of (start_date, end_date)
        """
        if view == 'month':
            # Get entire month
            start_date = target_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            last_day = monthrange(target_date.year, target_date.month)[1]
            end_date = target_date.replace(day=last_day, hour=23, minute=59, second=59)
        elif view == 'day':
            # Get single day
            start_date = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = target_date.replace(hour=23, minute=59, second=59)
        elif view == 'upcoming':
            # Get next 7 days from today (for upcoming events)
            start_date = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = start_date + timedelta(days=7)
            end_date = end_date.replace(hour=23, minute=59, second=59)
        else:  # week (default)
            # Get full week (Monday to Sunday)
            start_date = target_date - timedelta(days=target_date.weekday())
            start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = start_date + timedelta(days=7)
        
        return start_date, end_date
    
    @staticmethod
    def create_event(user, event_data):
        """
        Create a new calendar event.
        
        Args:
            user: User object
            event_data: Dictionary with event details (title, description, location, start, end)
            
        Returns:
            Event ID from Google Calendar
            
        Raises:
            ValidationError: If calendar not connected or event creation fails
        """
        if not user.calendar_sync_enabled:
            raise ValidationError("Calendar not connected")

        service = get_calendar_service(user)
        if not service:
            raise ValidationError("Failed to connect to Google Calendar")

        # Create event in Google Calendar
        event = {
            'summary': event_data.get('title'),
            'description': event_data.get('description', ''),
            'location': event_data.get('location', ''),
            'start': {
                'dateTime': event_data.get('start'),
                'timeZone': 'UTC',
            },
            'end': {
                'dateTime': event_data.get('end'),
                'timeZone': 'UTC',
            },
        }

        try:
            result = service.events().insert(calendarId='primary', body=event).execute()
            return result['id']
        except Exception as e:
            raise ValidationError(f"Failed to create event: {str(e)}")
    
    @staticmethod
    def sync_task(task_id, user_id):
        """
        Sync or update a task in Google Calendar.
        
        Args:
            task_id: ID of the task to sync
            user_id: ID of the user
            
        Returns:
            Success message
            
        Raises:
            NotFoundError: If task not found
            AuthorizationError: If user doesn't own the task
            ValidationError: If calendar not connected or sync fails
        """
        # Get the task from database
        task = db.session.get(Task, task_id)
        if not task:
            raise NotFoundError(f"Task with id {task_id} not found")

        # Security check - make sure user owns this task
        if task.user_id != user_id:
            raise AuthorizationError("You don't have permission to sync this task")

        # Check if Google Calendar is connected
        user = db.session.get(User, user_id)
        if not user.calendar_sync_enabled:
            raise ValidationError("Google Calendar not connected")

        # Get calendar service connection
        service = get_calendar_service(user)
        if not service:
            raise ValidationError("Failed to connect to Google Calendar")

        # Decide whether to update existing event or create new one
        if task.google_event_id:
            # Task already has a calendar event - update it
            success = update_calendar_event(service, task.google_event_id, task)
            message = 'Task updated in calendar'
        else:
            # Task not synced yet - create new calendar event
            event_id = create_calendar_event(service, task)
            if event_id:
                # Successfully created - save event ID to task
                task.google_event_id = event_id
                task.synced_to_calendar = True
                success = True
                message = 'Task synced to calendar'
            else:
                success = False
                message = 'Failed to sync task'

        # Save changes
        if success:
            db.session.commit()
            return message
        else:
            raise ValidationError(message)
    
    @staticmethod
    def remove_task_from_calendar(task_id, user_id):
        """
        Remove a task's event from Google Calendar.
        
        Args:
            task_id: ID of the task
            user_id: ID of the user
            
        Raises:
            NotFoundError: If task not found
            AuthorizationError: If user doesn't own the task
            ValidationError: If task not synced or removal fails
        """
        # Get the task from database
        task = db.session.get(Task, task_id)
        if not task:
            raise NotFoundError(f"Task with id {task_id} not found")

        # Security check - verify user owns this task
        if task.user_id != user_id:
            raise AuthorizationError("You don't have permission to modify this task")

        # Check if task is actually synced to calendar
        if not task.google_event_id:
            raise ValidationError("Task not synced to calendar")

        # Get calendar service connection
        user = db.session.get(User, user_id)
        service = get_calendar_service(user)
        if not service:
            raise ValidationError("Failed to connect to Google Calendar")

        # Delete the event from Google Calendar
        if delete_calendar_event(service, task.google_event_id):
            # Successfully deleted - clear the sync fields in database
            task.google_event_id = None
            task.synced_to_calendar = False
            db.session.commit()
        else:
            raise ValidationError("Failed to remove event from calendar")
    
    @staticmethod
    def update_event(user, event_id, event_data):
        """
        Update a Google Calendar event directly.
        
        Args:
            user: User object
            event_id: Google Calendar event ID
            event_data: Dictionary with updated fields
            
        Raises:
            ValidationError: If update fails
        """
        service = get_calendar_service(user)
        if not service:
            raise ValidationError("Google Calendar not connected")
        
        try:
            # Get the existing event from Google Calendar
            event = service.events().get(
                calendarId='primary',
                eventId=event_id
            ).execute()
            
            # Update the event fields
            if 'summary' in event_data:
                event['summary'] = event_data['summary']
            if 'description' in event_data:
                event['description'] = event_data['description']
            if 'location' in event_data:
                event['location'] = event_data['location']
            
            # Send the updated event back to Google Calendar
            service.events().update(
                calendarId='primary',
                eventId=event_id,
                body=event
            ).execute()
            
        except Exception as e:
            raise ValidationError(f"Error updating calendar event: {str(e)}")
    
    @staticmethod
    def delete_event(user, event_id):
        """
        Delete a Google Calendar event directly.
        
        Args:
            user: User object
            event_id: Google Calendar event ID
            
        Raises:
            ValidationError: If deletion fails
        """
        service = get_calendar_service(user)
        if not service:
            raise ValidationError("Google Calendar not connected")

        if not delete_calendar_event(service, event_id):
            raise ValidationError("Failed to delete event")
