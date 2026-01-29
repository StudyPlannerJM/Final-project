# type: ignore
# ==============================================================================
# MAIN ROUTES - All the URL endpoints for my app
# ==============================================================================

import json
import os
from flask import (
    Blueprint, render_template, request, redirect, url_for, flash, current_app
)
from werkzeug.utils import secure_filename
# Google Calendar integration functions
from app.google_calendar import (
    get_google_auth_flow, get_calendar_service,
    create_calendar_event, update_calendar_event,
    delete_calendar_event, get_upcoming_events,
    get_week_events, get_events_for_month
)
# Summarizer functions
from app.summarizer import (
    extract_text, generate_summary, get_allowed_extensions, get_file_type
)
from app.models import Task, Flashcard, Summary, Category
from app import db
from flask_login import login_required, current_user
from app.forms import TaskForm, FlashcardForm

# Blueprint: Groups related routes together
main = Blueprint('main', __name__)

# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

def sync_calendar_events_to_tasks(calendar_events, user):
    """
    Syncs Google Calendar events to local tasks.
    Creates tasks for calendar events that don't already exist in the database.
    
    Args:
        calendar_events: List of Google Calendar event dictionaries
        user: Current user object
    """
    from datetime import datetime
    
    for event in calendar_events:
        # Get event ID
        event_id = event.get('id')
        if not event_id:
            continue
            
        # Check if task already exists with this google_event_id
        existing_task = Task.query.filter_by(
            google_event_id=event_id,
            user_id=user.id
        ).first()
        
        if existing_task:
            continue  # Task already exists, skip
        
        # Get event details
        title = event.get('summary', 'Untitled Event')
        description = event.get('description', '')
        
        # Get start time
        start = event.get('start', {})
        due_date_str = start.get('dateTime') or start.get('date')
        
        if not due_date_str:
            continue  # Skip events without a date
        
        # Parse the date
        try:
            if 'T' in due_date_str:
                # DateTime format - remove timezone info and parse as naive datetime
                # Google Calendar sends times in the user's timezone already
                date_str_clean = due_date_str.split('+')[0].split('-', 3)[-1] if '+' in due_date_str else due_date_str.replace('Z', '')
                if '.' in date_str_clean:
                    date_str_clean = date_str_clean.split('.')[0]  # Remove microseconds
                due_date = datetime.strptime(date_str_clean, '%Y-%m-%dT%H:%M:%S')
            else:
                # Date only format
                due_date = datetime.strptime(due_date_str, '%Y-%m-%d')
        except Exception as e:
            print(f"Error parsing date {due_date_str}: {e}")
            continue  # Skip if date parsing fails
        
        # Create new task
        new_task = Task(
            title=title,
            description=description,
            due_date=due_date,
            category='Personal',  # Default category
            status='todo',
            user_id=user.id,
            google_event_id=event_id,
            synced_to_calendar=True
        )
        
        db.session.add(new_task)
    
    # Commit all new tasks
    try:
        db.session.commit()
    except Exception as e:
        print(f"Error syncing calendar events to tasks: {e}")
        db.session.rollback()


# ==============================================================================
# BASIC PAGE ROUTES
# ==============================================================================

@main.route('/')
@main.route('/dashboard')
@login_required
def dashboard():
    # Main landing page - shows after user logs in
    # This is the home page where users start their session
    return render_template(
        'dashboard.html', title='Dashboard'
    )


@main.route('/tasks')
@login_required
def tasks():
    # Display all my tasks organized by status (todo, doing, done)
    # This creates the Kanban board view with three columns
    
    # STEP 1: Get all "todo" tasks for current user, sorted by creation date
    todo_tasks = Task.query.filter_by(user_id=current_user.id, status="todo").order_by(
        Task.data_created.asc()
    ).all()
    
    # STEP 2: Get all "doing" (in progress) tasks
    doing_tasks = Task.query.filter_by(user_id=current_user.id, status="doing").order_by(
        Task.data_created.asc()
    ).all()
    
    # STEP 3: Get all "done" (completed) tasks
    done_tasks = Task.query.filter_by(user_id=current_user.id, status='done').order_by(
        Task.data_created.asc()
    ).all()
    
    # STEP 4: Pass all three lists to the template for display
    return render_template(
        'tasks.html', 
        title='Tasks', 
        todo_tasks=todo_tasks,
        doing_tasks=doing_tasks,
        done_tasks=done_tasks
    )
# ==============================================================================
# TASK MANAGEMENT ROUTES
# ==============================================================================

@main.route('/update_task_status/<int:task_id>/<status>', methods=['POST'])
@login_required
def update_task_status(task_id, status):
    # Update task status when dragging between Kanban columns
    # This is called via AJAX when user moves a task card
    
    # STEP 1: Get the task from database
    task = Task.query.get_or_404(task_id)

    # STEP 2: Security check - make sure current user owns this task
    if task.user_id != current_user.id:
        return {'success': False, 'error': 'Unauthorized'}, 403

    # STEP 3: Validate the new status is valid (todo, doing, or done)
    if status not in ['todo', 'doing', 'done']:
        return {'success': False, 'error': 'Invalid status'}, 400

    # STEP 4: Update the task's status and save to database
    task.status = status
    db.session.commit()

    # STEP 5: Return success response to JavaScript
    return {'success': True, 'task_id': task_id, 'new_status': status}

@main.route('/add_task', methods=['GET', 'POST'])
@login_required
def add_task():
    """
    Create a new task and optionally sync to Google Calendar.
    
    Handles both predefined categories and custom user-created categories.
    If Google Calendar sync is enabled, automatically creates a calendar event.
    """
    form = TaskForm()

    if form.validate_on_submit():
        # STEP 1: Determine which category to use
        # Form can have either a dropdown selection OR a custom typed category
        selected_category = form.category.data  # Category object from dropdown
        category_id = None

        # STEP 2: Handle custom category if user typed one in "Other" field
        if form.other_category.data and form.other_category.data.strip():
            category_name = form.other_category.data.strip().title()  # Normalize to Title Case

            # Check if this custom category already exists for this user
            category = Category.query.filter_by(
                user_id=current_user.id,
                name=category_name
            ).first()

            # Create new category if it doesn't exist yet
            if not category:
                category = Category(
                    name=category_name,
                    user_id=current_user.id,
                    is_default=False  # Mark as user-created (not system default)
                )
                db.session.add(category)
                db.session.flush()  # Get the ID without committing yet

            category_id = category.id
            
        # STEP 3: Use dropdown selection if no custom category was entered
        elif selected_category:
            category_id = selected_category.id
        # STEP 4: No category selected (category_id remains None)
        else:
            category_id = None          
        

        # STEP 5: Create the new task with all form data
        new_task = Task(
            title=form.title.data,
            description=form.description.data,
            due_date=form.due_date.data,
            category_id=category_id,  # Foreign key to Category table
            # BACKWARDS COMPATIBILITY: Keep old string field in sync for now
            category=selected_category.name if selected_category else None,
            author=current_user  # Links task to current logged-in user
        )

        # STEP 6: Save task to database
        db.session.add(new_task)
        db.session.commit()

        # STEP 7: Sync to Google Calendar if user has it enabled
        if current_user.calendar_sync_enabled and new_task.due_date:
            service = get_calendar_service(current_user)
            if service:
                # Create event on Google Calendar
                event_id = create_calendar_event(service, new_task)
                if event_id:
                    # Update task with Google event ID for future sync
                    new_task.google_event_id = event_id
                    new_task.synced_to_calendar = True
                    db.session.commit()

        # STEP 8: Show success message and return to tasks page
        flash('Task added successfully!', 'success')
        return redirect(url_for('main.tasks'))

    # GET request: Show empty form
    return render_template('add_task.html', title='Add New Task', form=form)

@main.route('/edit_task/<int:task_id>', methods=['GET', 'POST'])
@login_required
def edit_task(task_id):
    # Edit an existing task - modify title, description, date, or category
    # Pre-fills form with current task data   

    task = Task.query.get_or_404(task_id)

    if task.user_id != current_user.id:
        flash('You are not authorized to edit this task.', 'danger')
        return redirect(url_for('main.tasks'))

    form = TaskForm(obj=task)

    # On GET request, pre-select the category
    if request.method == "GET":
        if task.category_id:
            form.category.data = Category.query.get(task.category_id)

    if form.validate_on_submit():
        task.title = form.title.data
        task.description = form.description.data
        task.due_date = form.due_date.data

        # Handle category
        selected_category = form.category.data

        if form.other_category.data and form.other_category.data.strip():
            # Custom category
            category_name = form.other_category.data.strip().title()  # Normalize to Title Case
            category = Category.query.filter_by(
                user_id=current_user.id,
                name=category_name
            ).first()

            if not category:
                category = Category(
                    name=category_name,
                    user_id=current_user.id
                )
                db.session.add(category)
                db.session.flush()

            task.category_id = category.id
            task.category = category.name  # Keep old field in sync
        elif selected_category:
            task.category_id = selected_category.id
            task.category = selected_category.name
        else:
            task.category_id = None
            task.category = None

        db.session.commit()

        # Update Google Calendar if synced
        if current_user.calendar_sync_enabled and task.google_event_id:
            service = get_calendar_service(current_user)
            if service:
                update_calendar_event(service, task.google_event_id, task)

        flash("Your task has been updated!", "success")
        return redirect(url_for("main.tasks"))

    return render_template("edit_task.html", title="Edit Task", form=form, task=task)


@main.route('/delete_task/<int:task_id>', methods=['POST'])
@login_required
def delete_task(task_id):
    # Delete a task permanently from the database
    # Also removes from Google Calendar if synced
    task = Task.query.get_or_404(task_id)
    if task.user_id != current_user.id:
        flash('You are not authorized to delete this task.', 'danger')
        return redirect(url_for('main.tasks'))

    # Delete from Google Calendar if synced
    if task.google_event_id and current_user.calendar_sync_enabled:
        service = get_calendar_service(current_user)
        if service:
            delete_calendar_event(service, task.google_event_id)
            
    db.session.delete(task)
    db.session.commit()
    flash('Your task has been deleted!', 'success')
    return redirect(url_for('main.tasks'))


@main.route('/complete_task/<int:task_id>', methods=['POST'])
@login_required
def complete_task(task_id):
    # Toggle task completion status (mark as complete/incomplete)
    # This is separate from the status field (todo/doing/done)
    task = Task.query.get_or_404(task_id)
    if task.user_id != current_user.id:
        flash('You are not authorized to complete this task.', 'danger')
        return redirect(url_for('main.tasks'))
    task.is_complete = not task.is_complete
    db.session.commit()
    flash('Task status updated!', 'success')
    return redirect(url_for('main.tasks'))


# ==============================================================================
# UTILITY ROUTES
# ==============================================================================

@main.route('/settings')
@login_required
def settings():
    # User settings page
    return render_template('settings.html', title='Settings')


@main.route("/pomodoro")
@login_required
def pomodoro():
    # Pomodoro timer page - helps with time management using 25-minute work intervals
    return render_template("pomodoro.html", title="Pomodoro Timer")


# ==============================================================================
# FLASHCARD ROUTES
# ==============================================================================

@main.route("/flashcards")
@login_required
def flashcards():
    # Display all my flashcards for studying
    # Sorted by creation date (newest first)
    user_flashcards = Flashcard.query.filter_by(
        author=current_user
    ).order_by(Flashcard.date_created.desc()).all()
    return render_template(
        "flashcards.html", title="Flashcards", flashcards=user_flashcards
    )


@main.route("/add_flashcard", methods=["GET", "POST"])
@login_required
def add_flashcard():
    # Create a new flashcard with question and answer
    form = FlashcardForm()
    if form.validate_on_submit():
        new_flashcard = Flashcard(
            question=form.question.data,
            answer=form.answer.data,
            author=current_user
        )
        db.session.add(new_flashcard)
        db.session.commit()
        flash("Your flashcard has been added!", "success")
        return redirect(url_for("main.flashcards"))
    return render_template(
        "add_flashcards.html", title="Add Flashcard", form=form
    )


@main.route("/edit_flashcard/<int:flashcard_id>", methods=["GET", "POST"])
@login_required
def edit_flashcard(flashcard_id):
    # Edit an existing flashcard - update question or answer
    flashcard = Flashcard.query.get_or_404(flashcard_id)
    if flashcard.author != current_user:
        flash("You are not authorized to edit this flashcard.", "danger")
        return redirect(url_for("main.flashcards"))

    form = FlashcardForm(obj=flashcard)
    if form.validate_on_submit():
        flashcard.question = form.question.data
        flashcard.answer = form.answer.data
        db.session.commit()
        flash("Your flashcard has been updated!", "success")
        return redirect(url_for("main.flashcards"))
    return render_template(
        "edit_flashcards.html",
        title="Edit Flashcard",
        form=form,
        flashcard=flashcard
    )


@main.route("/delete_flashcard/<int:flashcard_id>", methods=["POST"])
@login_required
def delete_flashcard(flashcard_id):
    # Delete a flashcard
    flashcard = Flashcard.query.get_or_404(flashcard_id)
    if flashcard.author != current_user:
        flash("You are not authorized to delete this flashcard.", "danger")
        return redirect(url_for("main.flashcards"))

    db.session.delete(flashcard)
    db.session.commit()
    flash("Your flashcard has been deleted!", "success")
    return redirect(url_for("main.flashcards"))

# ==============================================================================
# GOOGLE CALENDAR INTEGRATION ROUTES
# ==============================================================================
@main.route('/authorize_google')
@login_required
def authorize_google():
    # Start Google OAuth flow - redirects user to Google login page
    # After user authorizes, Google redirects back to oauth2callback
    flow = get_google_auth_flow()
    authorization_url, state = flow.authorization_url(
        access_type='offline',  # Get refresh token
        include_granted_scopes='true',
        prompt='consent'  # Force consent screen
    )
    # Store state for CSRF protection
    from flask import session
    session['state'] = state
    return redirect(authorization_url)

@main.route('/oauth2callback')
@login_required
def oauth2callback():
    # Handle Google's redirect after user authorizes my app
    # Extract and save the access token to database
    from flask import session

    state = session.get('state')  # Verify CSRF protection

    flow = get_google_auth_flow()
    flow.fetch_token(authorization_response=request.url)

    credentials = flow.credentials

    # Save credentials to database as JSON
    token_data = {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes
    }

    current_user.google_token = json.dumps(token_data)
    current_user.calendar_sync_enabled = True
    db.session.commit()

    flash('Google Calendar connected successfully!', 'success')
    return redirect(url_for('main.schedule'))

@main.route('/disconnect_google')
@login_required
def disconnect_google():
    # Remove Google Calendar connection - clear stored token
    # User will need to re-authorize to use calendar features again
    current_user.google_token = None
    current_user.calendar_sync_enabled = False
    db.session.commit()

    flash('Google Calendar disconnected.', 'info')
    return redirect(url_for('main.schedule'))

@main.route('/schedule')
@login_required
def schedule():
    """
    Enhanced schedule page with week view calendar.
    Shows mini calendar, week view, and upcoming events.
    """
    from datetime import datetime, timedelta

    # Get date parameter (if navigating to specific date)
    date_param = request.args.get('date')
    if date_param:
        try:
            target_date = datetime.strptime(date_param, '%Y-%m-%d')
        except:
            target_date = datetime.now()
    else:
        target_date = datetime.now()

    # Get all tasks sorted by due date
    tasks = Task.query.filter_by(user_id=current_user.id).order_by(
        Task.due_date.asc()
    ).all()

    # Initialize calendar variables
    calendar_events = []
    week_events = []
    month_events = {}
    calendar_connected = False
    upcoming_events = []

    # Check if Google Calendar is connected
    if current_user.calendar_sync_enabled:
        service = get_calendar_service(current_user)
        if service:
            try:
                calendar_connected = True

                # Get events for the week view
                week_events = get_week_events(service, target_date)

                # Get events for the mini calendar (current month)
                month_events = get_events_for_month(
                    service, 
                    target_date.year, 
                    target_date.month
                )

                # Get upcoming events (within next 7 days from TODAY)
                upcoming_events = get_upcoming_events(service, max_results=20)
                print(f"DEBUG: Fetched {len(upcoming_events)} upcoming events from Google Calendar")
                
                # Filter out Google Calendar events that match local tasks (to avoid duplicates)
                synced_event_ids = [task.google_event_id for task in tasks if task.google_event_id]
                week_events = [e for e in week_events if e.get('id') not in synced_event_ids]
                upcoming_events = [e for e in upcoming_events if e.get('id') not in synced_event_ids]
                
                print(f"DEBUG: Passing {len(week_events)} events to week view")
                print(f"DEBUG: Google Calendar events for upcoming: {len(upcoming_events)}")
                
            except Exception as e:
                # Token expired or other error - disconnect calendar
                print(f"Calendar error: {e}")
                current_user.google_token = None
                current_user.calendar_sync_enabled = False
                db.session.commit()
                calendar_connected = False
                flash('Your Google Calendar connection has expired. Please reconnect.', 'warning')

    # Add local tasks to upcoming events (tasks with due dates in the next 7 days)
    now = datetime.now()
    week_from_now = now + timedelta(days=7)
    upcoming_tasks = [task for task in tasks if task.due_date and now <= task.due_date <= week_from_now]
    
    # Convert tasks to event format for display in upcoming section
    for task in upcoming_tasks:
        upcoming_events.append({
            'id': f'task_{task.id}',
            'title': task.title,
            'start': task.due_date.isoformat(),
            'end': task.due_date.isoformat(),
            'description': task.description or '',
            'location': '',
            'color': '#6c757d',  # Gray color for local tasks
            'color_transparent': 'rgba(108, 117, 125, 0.1)',
            'htmlLink': '',
            'isLocalTask': True
        })
    
    # Sort all upcoming events by start time
    upcoming_events.sort(key=lambda x: x['start'])
    print(f"DEBUG: Total upcoming events (Google + Local): {len(upcoming_events)}")

    # Prepare week dates for the template
    start_of_week = target_date - timedelta(days=target_date.weekday())
    week_dates = []
    for i in range(7):
        day = start_of_week + timedelta(days=i)
        week_dates.append({
            'date': day,
            'day_name': day.strftime('%A'),
            'day_num': day.day,
            'is_today': day.date() == target_date.date()
        })

    # Prepare tasks data for JavaScript
    tasks_json = []
    for task in tasks:
        if task.due_date:
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

    return render_template(
        'schedule.html',
        title='Schedule',
        tasks=tasks,
        tasks_json=tasks_json,
        calendar_connected=calendar_connected,
        week_events=week_events,
        month_events=month_events,
        upcoming_events=upcoming_events,
        week_dates=week_dates,
        target_date=target_date,
        current_month=target_date.strftime('%B, %Y')
    )
    
@main.route('/api/calendar/week')
@login_required
def api_week_events():
    """
    API endpoint to get events for a specific week.
    Used for AJAX updates when navigating calendar.
    """
    from datetime import datetime

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
    
@main.route('/api/calendar/event', methods=['POST'])
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
    
@main.route('/sync_task_to_calendar/<int:task_id>', methods=['POST'])
@login_required
def sync_task_to_calendar(task_id):
    # Sync or update a task in Google Calendar
    # Creates new calendar event if task not synced yet, otherwise updates existing event
    
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
    
@main.route('/remove_task_from_calendar/<int:task_id>', methods=['POST'])
@login_required
def remove_task_from_calendar(task_id):
    # Remove a task's event from Google Calendar
    # Keeps the task in my database, just removes from calendar
    
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


@main.route('/update_calendar_event/<event_id>', methods=['POST'])
@login_required
def update_calendar_event_route(event_id):
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


@main.route('/delete_calendar_event/<event_id>', methods=['POST'])
@login_required
def delete_calendar_event_route(event_id):
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


# ==============================================================================
# SUMMARIZER ROUTES
# ==============================================================================

def allowed_file(filename):
    """Check if the file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in get_allowed_extensions()


@main.route('/summarizer')
@login_required
def summarizer():
    """Display all summaries for the current user"""
    user_summaries = Summary.query.filter_by(
        author=current_user
    ).order_by(Summary.date_created.desc()).all()
    return render_template(
        'summarizer.html', title='Summarizer', summaries=user_summaries
    )


@main.route('/upload_summary', methods=['GET', 'POST'])
@login_required
def upload_summary():
    """Upload a file and create a summary"""
    if request.method == 'POST':
        # STEP 1: Check if file was uploaded
        if 'file' not in request.files:
            flash('No file selected. Please choose a file to upload.', 'danger')
            return redirect(request.url)
        
        file = request.files['file']
        
        # STEP 2: Check if a file was actually selected
        if file.filename == '':
            flash('No file selected. Please choose a file to upload.', 'danger')
            return redirect(request.url)
        
        # STEP 3: Validate file type
        if not allowed_file(file.filename):
            flash('Invalid file type. Allowed types: PDF, DOCX, JPG, PNG, GIF, BMP, TIFF', 'danger')
            return redirect(request.url)
        
        # STEP 4: Get the title from form or use filename
        title = request.form.get('title', '').strip()
        if not title:
            title = os.path.splitext(file.filename)[0]
        
        # STEP 5: Save the file temporarily
        filename = secure_filename(file.filename)
        upload_folder = os.path.join(current_app.root_path, 'uploads')
        os.makedirs(upload_folder, exist_ok=True)
        file_path = os.path.join(upload_folder, filename)
        file.save(file_path)
        
        try:
            # STEP 6: Determine file type and extract text
            file_type = get_file_type(filename)
            
            # Check if user wants to use OCR for PDF
            use_ocr = request.form.get('use_ocr') == 'on'
            if file_type == 'pdf' and use_ocr:
                file_type = 'ocr'
            
            success, result = extract_text(file_path, file_type)
            
            if not success:
                flash(f'Error extracting text: {result}', 'danger')
                return redirect(request.url)
            
            extracted_text = result
            
            # STEP 7: Generate summary
            summary_text = generate_summary(extracted_text)
            
            # STEP 8: Create new Summary record
            new_summary = Summary(
                title=title,
                original_filename=filename,
                extracted_text=extracted_text,
                summary_text=summary_text,
                file_type=file_type,
                author=current_user
            )
            
            db.session.add(new_summary)
            db.session.commit()
            
            flash('Document processed successfully! Summary created.', 'success')
            return redirect(url_for('main.view_summary', summary_id=new_summary.id))
            
        except Exception as e:
            flash(f'Error processing document: {str(e)}', 'danger')
            return redirect(request.url)
        finally:
            # STEP 9: Clean up - delete temporary file
            if os.path.exists(file_path):
                os.remove(file_path)
    
    return render_template('upload_summary.html', title='Upload Document')


@main.route('/view_summary/<int:summary_id>')
@login_required
def view_summary(summary_id):
    """View a specific summary"""
    summary = Summary.query.get_or_404(summary_id)
    
    # Security check - verify user owns this summary
    if summary.author != current_user:
        flash('You are not authorized to view this summary.', 'danger')
        return redirect(url_for('main.summarizer'))
    
    return render_template(
        'view_summary.html', title='View Summary', summary=summary
    )


@main.route('/delete_summary/<int:summary_id>', methods=['POST'])
@login_required
def delete_summary(summary_id):
    """Delete a summary"""
    summary = Summary.query.get_or_404(summary_id)
    
    # Security check - verify user owns this summary
    if summary.author != current_user:
        flash('You are not authorized to delete this summary.', 'danger')
        return redirect(url_for('main.summarizer'))
    
    db.session.delete(summary)
    db.session.commit()
    flash('Summary deleted successfully!', 'success')
    return redirect(url_for('main.summarizer'))