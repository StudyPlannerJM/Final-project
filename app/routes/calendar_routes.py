"""
Calendar Routes Blueprint - Google Calendar integration routes
"""
import json
from datetime import datetime, timedelta
from calendar import monthrange
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import login_required, current_user
from app.models import Task
from app import db
from app.utils.calendar_client import (
    get_google_auth_flow,
    get_calendar_service,
    sync_unsynced_tasks_to_calendar,
    get_events_for_date_range,
    get_week_events,
    create_calendar_event,
    update_calendar_event,
    delete_calendar_event
)

calendar_bp = Blueprint('calendar', __name__, url_prefix='/calendar')


@calendar_bp.route('/authorize')
@login_required
def authorize_google():
    """Start Google OAuth flow - redirects user to Google login page"""
    flow = get_google_auth_flow()
    authorization_url, state = flow.authorization_url(
        access_type='offline',  # Get refresh token
        include_granted_scopes='true',
        prompt='consent'  # Force consent screen
    )
    # Store state for CSRF protection
    session['state'] = state
    return redirect(authorization_url)


@calendar_bp.route('/oauth2callback')
@login_required
def oauth2callback():
    """Handle Google's redirect after user authorizes"""
    state = session.get('state')  # Verify CSRF protection

    flow = get_google_auth_flow()
    flow.fetch_token(authorization_response=request.url)

    credentials = flow.credentials

    # Save credentials to database as JSON
    token_data = {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,  # type: ignore
        'client_id': credentials.client_id,  # type: ignore
        'client_secret': credentials.client_secret,  # type: ignore
        'scopes': credentials.scopes
    }

    current_user.google_token = json.dumps(token_data)
    current_user.calendar_sync_enabled = True
    db.session.commit()

    flash('Google Calendar connected successfully!', 'success')
    
    # Check if user has existing tasks with due dates that could be synced
    unsynced_count = Task.query.filter_by(
        user_id=current_user.id,
        synced_to_calendar=False
    ).filter(Task.due_date.isnot(None)).count()  # type: ignore
    
    if unsynced_count > 0:
        # Redirect to sync prompt
        return redirect(url_for('calendar.sync_prompt', count=unsynced_count))
    else:
        # No tasks to sync, go directly to schedule
        return redirect(url_for('calendar.schedule'))


@calendar_bp.route('/sync_prompt')
@login_required
def sync_prompt():
    """
    Show prompt asking user if they want to sync existing tasks to Google Calendar.
    This is shown after first connecting Google Calendar.
    """
    count = request.args.get('count', 0, type=int)
    
    if not current_user.calendar_sync_enabled:
        flash('Please connect Google Calendar first.', 'warning')
        return redirect(url_for('calendar.schedule'))
    
    return render_template('calendar/calendar_sync_prompt.html', 
                         title='Sync Tasks to Calendar',
                         count=count)


@calendar_bp.route('/sync_existing_tasks', methods=['POST'])
@login_required
def sync_existing_tasks():
    """
    Sync all existing unsynced tasks to Google Calendar.
    Called when user clicks 'Yes, Sync All' on the prompt.
    """
    if not current_user.calendar_sync_enabled:
        flash('Google Calendar not connected.', 'danger')
        return redirect(url_for('calendar.schedule'))
    
    success_count, total_count = sync_unsynced_tasks_to_calendar(current_user)
    
    if success_count == total_count:
        flash(f'Successfully synced {success_count} tasks to Google Calendar!', 'success')
    elif success_count > 0:
        flash(f'Synced {success_count} out of {total_count} tasks. Some tasks may have failed.', 'warning')
    else:
        flash('Failed to sync tasks to Google Calendar.', 'danger')
    
    return redirect(url_for('calendar.schedule'))


@calendar_bp.route('/skip_sync_existing_tasks', methods=['POST'])
@login_required
def skip_sync_existing_tasks():
    """Skip syncing existing tasks. Only new tasks will auto-sync."""
    flash('Only new tasks will be synced to Google Calendar.', 'info')
    return redirect(url_for('calendar.schedule'))


@calendar_bp.route('/disconnect')
@login_required
def disconnect_google():
    """Remove Google Calendar connection - clear stored token"""
    current_user.google_token = None
    current_user.calendar_sync_enabled = False
    db.session.commit()

    flash('Google Calendar disconnected.', 'info')
    return redirect(url_for('calendar.schedule'))


@calendar_bp.route('/schedule')
@login_required
def schedule():
    """
    Simplified schedule page - just renders HTML skeleton.
    JavaScript will fetch all data via AJAX.
    """
    # Get parameters from URL
    date_param = request.args.get('date')
    view_param = request.args.get('view', 'week')
    
    if date_param:
        try:
            target_date = datetime.strptime(date_param, '%Y-%m-%d')
        except:
            target_date = datetime.now()
    else:
        target_date = datetime.now()

    # Check if Google Calendar is connected (just a boolean check)
    calendar_connected = current_user.calendar_sync_enabled and current_user.google_token is not None

    # Pass minimal data to template - JavaScript will load the rest
    return render_template(
        'calendar/schedule.html',
        title='Schedule',
        calendar_connected=calendar_connected,
        target_date=target_date,
        view=view_param,
        current_month=target_date.strftime('%B, %Y')
    )


# ==============================================================================
# CALENDAR API ENDPOINTS
# ==============================================================================

@calendar_bp.route('/api/events')
@login_required
def api_calendar_events():
    """
    UNIFIED API endpoint to get ALL calendar data for any date range.
    Returns JSON instead of HTML.
    """
    # Parse parameters from URL
    date_str = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    view = request.args.get('view', 'week')
    
    try:
        target_date = datetime.strptime(date_str, '%Y-%m-%d')
    except Exception as e:
        return jsonify({'success': False, 'error': 'Invalid date format'}), 400

    # Calculate date range based on view type
    if view == 'month':
        # Get entire month
        start_date = target_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        last_day = monthrange(target_date.year, target_date.month)[1]
        end_date = target_date.replace(day=last_day, hour=23, minute=59, second=59)
    elif view == 'day':
        # Get single day
        start_date = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = target_date.replace(hour=23, minute=59, second=59)
    else:  # week (default)
        # Get full week (Monday to Sunday)
        start_date = target_date - timedelta(days=target_date.weekday())
        start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(days=7)

    # Fetch Google Calendar events (if connected)
    calendar_events = []
    calendar_connected = False
    
    if current_user.calendar_sync_enabled and current_user.google_token:
        service = get_calendar_service(current_user)
        if service:
            try:
                calendar_events = get_events_for_date_range(service, start_date, end_date)
                calendar_connected = True
            except Exception as e:
                print(f"Error fetching calendar events: {e}")
                calendar_connected = False

    # Fetch local tasks for the date range
    tasks = Task.query.filter(
        Task.user_id == current_user.id,  # type: ignore
        Task.due_date.isnot(None),  # type: ignore
        Task.due_date >= start_date,  # type: ignore
        Task.due_date <= end_date  # type: ignore
    ).order_by(Task.due_date.asc()).all()  # type: ignore

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
        start_of_week = target_date - timedelta(days=target_date.weekday())
        for i in range(7):
            day = start_of_week + timedelta(days=i)
            week_dates.append({
                'date': day.strftime('%Y-%m-%d'),
                'day_name': day.strftime('%A'),
                'day_num': day.day,
                'is_today': day.date() == datetime.now().date()
            })

    return jsonify({
        'success': True,
        'calendarConnected': calendar_connected,
        'calendarEvents': calendar_events,
        'tasks': tasks_json,
        'weekDates': week_dates,
        'targetDate': target_date.strftime('%Y-%m-%d'),
        'currentMonth': target_date.month,
        'currentYear': target_date.year,
        'view': view
    })


@calendar_bp.route('/api/week')
@login_required
def api_week_events():
    """
    API endpoint to get events for a specific week.
    Used for AJAX updates when navigating calendar.
    """
    date_str = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    try:
        target_date = datetime.strptime(date_str, '%Y-%m-%d')
    except:
        return {'success': False, 'error': 'Invalid date format'}, 400

    if not current_user.calendar_sync_enabled:
        return {'success': False, 'error': 'Calendar not connected'}, 400

    service = get_calendar_service(current_user)
    if not service:
        return {'success': False, 'error': 'Failed to connect'}, 500

    week_events = get_week_events(service, target_date)

    return {
        'success': True,
        'events': week_events
    }


@calendar_bp.route('/api/create_event', methods=['POST'])
@login_required
def api_create_event():
    """
    API endpoint to create a new calendar event.
    Called from the event dialog modal.
    """
    if not current_user.calendar_sync_enabled:
        return {'success': False, 'error': 'Calendar not connected'}, 400

    service = get_calendar_service(current_user)
    if not service:
        return {'success': False, 'error': 'Failed to connect'}, 500

    data = request.get_json()

    # Create event in Google Calendar
    event = {
        'summary': data.get('title'),
        'description': data.get('description', ''),
        'location': data.get('location', ''),
        'start': {
            'dateTime': data.get('start'),
            'timeZone': 'UTC',
        },
        'end': {
            'dateTime': data.get('end'),
            'timeZone': 'UTC',
        },
    }

    try:
        result = service.events().insert(calendarId='primary', body=event).execute()
        return {
            'success': True,
            'event_id': result['id'],
            'message': 'Event created successfully'
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}, 500


@calendar_bp.route('/sync_task/<int:task_id>', methods=['POST'])
@login_required
def sync_task(task_id):
    """
    Sync or update a task in Google Calendar.
    Creates new calendar event if task not synced yet, otherwise updates existing event.
    """
    # STEP 1: Get the task from database
    task = Task.query.get_or_404(task_id)

    # STEP 2: Security check - make sure user owns this task
    if task.user_id != current_user.id:
        return {'success': False, 'error': 'Unauthorized'}, 403

    # STEP 3: Check if Google Calendar is connected
    if not current_user.calendar_sync_enabled:
        return {
            'success': False,
            'error': 'Google Calendar not connected'
        }, 400

    # STEP 4: Get calendar service connection
    service = get_calendar_service(current_user)
    if not service:
        return {
            'success': False,
            'error': 'Failed to connect to Google Calendar'
        }, 500

    # STEP 5: Decide whether to update existing event or create new one
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

    # STEP 6: Save changes and return response
    if success:
        db.session.commit()
        return {'success': True, 'message': message}
    else:
        return {'success': False, 'error': message}, 500


@calendar_bp.route('/remove_task/<int:task_id>', methods=['POST'])
@login_required
def remove_task(task_id):
    """
    Remove a task's event from Google Calendar.
    Keeps the task in database, just removes from calendar.
    """
    # STEP 1: Get the task from database
    task = Task.query.get_or_404(task_id)

    # STEP 2: Security check - verify user owns this task
    if task.user_id != current_user.id:
        return {'success': False, 'error': 'Unauthorized'}, 403

    # STEP 3: Check if task is actually synced to calendar
    if not task.google_event_id:
        return {'success': False, 'error': 'Task not synced'}, 400

    # STEP 4: Get calendar service connection
    service = get_calendar_service(current_user)
    if not service:
        return {'success': False, 'error': 'Failed to connect'}, 500

    # STEP 5: Delete the event from Google Calendar
    if delete_calendar_event(service, task.google_event_id):
        # Successfully deleted - clear the sync fields in database
        task.google_event_id = None
        task.synced_to_calendar = False
        db.session.commit()
        return {'success': True, 'message': 'Removed from calendar'}
    else:
        # Failed to delete from calendar
        return {'success': False, 'error': 'Failed to remove'}, 500


@calendar_bp.route('/update_event/<event_id>', methods=['POST'])
@login_required
def update_event(event_id):
    """
    Update a Google Calendar event directly.
    Used for editing events from the upcoming events section.
    """
    # STEP 1: Check if Google Calendar is connected
    service = get_calendar_service(current_user)
    if not service:
        return {'success': False, 'error': 'Google Calendar not connected'}, 500

    # STEP 2: Get the update data from request
    data = request.get_json()
    
    try:
        # STEP 3: Get the existing event from Google Calendar
        event = service.events().get(
            calendarId='primary',
            eventId=event_id
        ).execute()
        
        # STEP 4: Update the event fields
        if 'summary' in data:
            event['summary'] = data['summary']
        if 'description' in data:
            event['description'] = data['description']
        if 'location' in data:
            event['location'] = data['location']
        
        # STEP 5: Send the updated event back to Google Calendar
        updated_event = service.events().update(
            calendarId='primary',
            eventId=event_id,
            body=event
        ).execute()
        
        return {'success': True, 'message': 'Event updated successfully'}
    
    except Exception as e:
        print(f"Error updating calendar event: {e}")
        return {'success': False, 'error': str(e)}, 500


@calendar_bp.route('/delete_event/<event_id>', methods=['POST'])
@login_required
def delete_event(event_id):
    """
    Delete a Google Calendar event directly.
    Used for deleting events from the upcoming events section.
    """
    # STEP 1: Check if Google Calendar is connected
    service = get_calendar_service(current_user)
    if not service:
        return {'success': False, 'error': 'Google Calendar not connected'}, 500

    # STEP 2: Delete the event from Google Calendar
    if delete_calendar_event(service, event_id):
        return {'success': True, 'message': 'Event deleted successfully'}
    else:
        return {'success': False, 'error': 'Failed to delete event'}, 500
