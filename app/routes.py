# type: ignore
# ==============================================================================
# MAIN ROUTES - All the URL endpoints for my app
# ==============================================================================

import json
from flask import (
    Blueprint, render_template, request, redirect, url_for, flash
)
# Google Calendar integration functions
from app.google_calendar import (
    get_google_auth_flow, get_calendar_service,
    create_calendar_event, update_calendar_event,
    delete_calendar_event, get_upcoming_events
)
from app.models import Task, Flashcard
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
    # Show schedule page with tasks and Google Calendar events combined
    # If calendar is connected, fetch upcoming events from Google
    
    # STEP 1: Get all my tasks sorted by due date (earliest first)
    tasks = Task.query.filter_by(user_id=current_user.id).order_by(
        Task.due_date.asc()
    ).all()

    # STEP 2: Initialize calendar variables
    calendar_events = []
    calendar_connected = False

    # STEP 3: Check if I've connected Google Calendar
    if current_user.calendar_sync_enabled:
        # Try to get calendar service
        service = get_calendar_service(current_user)
        if service:
            # Successfully connected - mark as connected and fetch events
            calendar_connected = True
            calendar_events = get_upcoming_events(service, max_results=20)

    # STEP 4: Render the schedule page with all data
    return render_template(
        'schedule.html',
        title='Schedule',
        tasks=tasks,
        calendar_events=calendar_events,
        calendar_connected=calendar_connected
    )