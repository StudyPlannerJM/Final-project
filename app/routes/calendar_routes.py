"""
Calendar Routes Blueprint - Google Calendar integration routes
"""
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import login_required, current_user
from app.services import CalendarService
from app.utils.calendar_client import get_google_auth_flow
from app.exceptions import ValidationError, AuthorizationError, NotFoundError

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

    # Connect Google Calendar using service
    unsynced_count = CalendarService.connect_google_calendar(current_user, credentials)

    flash('Google Calendar connected successfully!', 'success')
    
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
    try:
        success_count, total_count = CalendarService.sync_existing_tasks(current_user)
        
        if success_count == total_count:
            flash(f'Successfully synced {success_count} tasks to Google Calendar!', 'success')
        elif success_count > 0:
            flash(f'Synced {success_count} out of {total_count} tasks. Some tasks may have failed.', 'warning')
        else:
            flash('Failed to sync tasks to Google Calendar.', 'danger')
    except ValidationError as e:
        flash(str(e), 'danger')
    
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
    try:
        CalendarService.disconnect_google_calendar(current_user.id)
        flash('Google Calendar disconnected.', 'info')
    except NotFoundError as e:
        flash(str(e), 'danger')
    
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

    # Calculate date range based on view type using service
    start_date, end_date = CalendarService.calculate_date_range(target_date, view)
    
    # Get calendar events and tasks using service
    result = CalendarService.get_calendar_events(current_user, start_date, end_date, view)

    return jsonify({
        'success': True,
        'calendarConnected': result['calendar_connected'],
        'calendarEvents': result['calendar_events'],
        'tasks': result['tasks'],
        'weekDates': result['week_dates'],
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
    Legacy endpoint - consider using /api/events?view=week instead.
    """
    date_str = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    try:
        target_date = datetime.strptime(date_str, '%Y-%m-%d')
    except:
        return {'success': False, 'error': 'Invalid date format'}, 400

    try:
        # Use the unified calendar events method
        start_date, end_date = CalendarService.calculate_date_range(target_date, 'week')
        result = CalendarService.get_calendar_events(current_user, start_date, end_date, 'week')
        
        return {
            'success': True,
            'events': result['calendar_events'] + result['tasks']
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}, 500



@calendar_bp.route('/api/create_event', methods=['POST'])
@login_required
def api_create_event():
    """
    API endpoint to create a new calendar event.
    Called from the event dialog modal.
    """
    try:
        data = request.get_json()
        event_id = CalendarService.create_event(current_user, data)
        return {
            'success': True,
            'event_id': event_id,
            'message': 'Event created successfully'
        }
    except ValidationError as e:
        return {'success': False, 'error': str(e)}, 400
    except Exception as e:
        return {'success': False, 'error': str(e)}, 500


@calendar_bp.route('/sync_task/<int:task_id>', methods=['POST'])
@login_required
def sync_task(task_id):
    """
    Sync or update a task in Google Calendar.
    Creates new calendar event if task not synced yet, otherwise updates existing event.
    """
    try:
        message = CalendarService.sync_task(task_id, current_user.id)
        return {'success': True, 'message': message}
    except NotFoundError as e:
        return {'success': False, 'error': str(e)}, 404
    except AuthorizationError as e:
        return {'success': False, 'error': str(e)}, 403
    except ValidationError as e:
        return {'success': False, 'error': str(e)}, 400
    except Exception as e:
        return {'success': False, 'error': str(e)}, 500


@calendar_bp.route('/remove_task/<int:task_id>', methods=['POST'])
@login_required
def remove_task(task_id):
    """
    Remove a task's event from Google Calendar.
    Keeps the task in database, just removes from calendar.
    """
    try:
        CalendarService.remove_task_from_calendar(task_id, current_user.id)
        return {'success': True, 'message': 'Removed from calendar'}
    except NotFoundError as e:
        return {'success': False, 'error': str(e)}, 404
    except AuthorizationError as e:
        return {'success': False, 'error': str(e)}, 403
    except ValidationError as e:
        return {'success': False, 'error': str(e)}, 400
    except Exception as e:
        return {'success': False, 'error': str(e)}, 500


@calendar_bp.route('/update_event/<event_id>', methods=['POST'])
@login_required
def update_event(event_id):
    """
    Update a Google Calendar event directly.
    Used for editing events from the upcoming events section.
    """
    try:
        data = request.get_json()
        CalendarService.update_event(current_user, event_id, data)
        return {'success': True, 'message': 'Event updated successfully'}
    except ValidationError as e:
        return {'success': False, 'error': str(e)}, 400
    except Exception as e:
        return {'success': False, 'error': str(e)}, 500


@calendar_bp.route('/delete_event/<event_id>', methods=['POST'])
@login_required
def delete_event(event_id):
    """
    Delete a Google Calendar event directly.
    Used for deleting events from the upcoming events section.
    """
    try:
        CalendarService.delete_event(current_user, event_id)
        return {'success': True, 'message': 'Event deleted successfully'}
    except ValidationError as e:
        return {'success': False, 'error': str(e)}, 400
    except Exception as e:
        return {'success': False, 'error': str(e)}, 500
