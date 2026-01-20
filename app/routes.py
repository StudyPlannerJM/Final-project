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
    delete_calendar_event, get_upcoming_events
)
# Summarizer functions
from app.summarizer import (
    extract_text, generate_summary, get_allowed_extensions, get_file_type
)
from app.models import Task, Flashcard, Summary
from app import db
from flask_login import login_required, current_user
from app.forms import TaskForm, FlashcardForm

# Blueprint: Groups related routes together
main = Blueprint('main', __name__)


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
    # Create a new task with title, description, due date, and category
    # Shows form on GET, processes submission on POST
    
    form = TaskForm()
    
    if form.validate_on_submit():
        # STEP 1: Handle custom category
        # If user selected "Other", use the custom text they entered
        category = form.category.data
        if category == "Other" and form.other_category.data.strip():
            category = form.other_category.data.strip()

        # STEP 2: Create new task object with form data
        new_task = Task(
            title=form.title.data,
            description=form.description.data,
            due_date=form.due_date.data,
            category=category,
            author=current_user  # Link task to current user
        )
        
        # STEP 3: Save to database
        db.session.add(new_task)
        db.session.commit()
        
        # STEP 4: Show success message and redirect to tasks page
        flash('Task added successfully!', 'success')
        return redirect(url_for('main.tasks'))
    
    # If GET request, just show the form
    return render_template('add_task.html', title='Add New Task', form=form)


@main.route('/edit_task/<int:task_id>', methods=['GET', 'POST'])
@login_required
def edit_task(task_id):
    # Edit an existing task - modify title, description, date, or category
    # Pre-fills form with current task data
    
    # STEP 1: Get the task from database
    task = Task.query.get_or_404(task_id)
    
    # STEP 2: Security check - verify user owns this task
    if task.user_id != current_user.id:
        flash('You are not authorized to edit this task.', 'danger')
        return redirect(url_for('main.tasks'))

    # STEP 3: Create form pre-filled with task data
    form = TaskForm(obj=task)

    # STEP 4: On GET request, handle custom categories
    # If task has a custom category (not in default list), set form to "Other"
    if request.method == "GET":
        default_choices = [c[0] for c in form.category.choices]
        if task.category not in default_choices:
            form.category.data = "Other"
            form.other_category.data = task.category

    # STEP 5: On POST (form submission), update the task
    if form.validate_on_submit():
        task.title = form.title.data
        task.description = form.description.data
        task.due_date = form.due_date.data

        # Handle custom category
        category = form.category.data
        if category == "Other" and form.other_category.data.strip():
            category = form.other_category.data.strip()
        task.category = category

        # Save changes to database
        db.session.commit()
        flash("Your task has been updated!", "success")
        return redirect(url_for("main.tasks"))
    
    return render_template(
        "edit_task.html", title="Edit Task", form=form, task=task
    )


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
            calendar_connected = True

            # Get events for the week view
            week_events = get_week_events(service, target_date)

            # Get events for the mini calendar (current month)
            month_events = get_events_for_month(
                service, 
                target_date.year, 
                target_date.month
            )

            # Get upcoming events (next 7 events from today)
            upcoming_events = get_upcoming_events(service, max_results=7)

    # Prepare week dates for the template
    start_of_week = target_date - timedelta(days=target_date.weekday())
    week_dates = []
    for i in range(7):
        day = start_of_week + timedelta(days=i)
        week_dates.append({
            'date': day,
            'day_name': day.strftime('%A'),
            'day_num': day.day,
            'is_today': day.date() == datetime.now().date()
        })

    return render_template(
        'schedule.html',
        title='Schedule',
        tasks=tasks,
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