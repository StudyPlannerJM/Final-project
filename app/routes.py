# type: ignore
# ==============================================================================
# MAIN ROUTES - All the URL endpoints for my app
# ==============================================================================

import json
import os
from datetime import datetime, timedelta
from app.models import StudySession, PomodoroSession

from flask import (
    Blueprint, render_template, request, redirect, url_for, flash, current_app, jsonify
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
# AI Planner functions
from app.ai_planner import generate_study_plan, format_plan_for_display
from app.models import Task, Flashcard, Summary, Category, StudyPlan
from app import db
from flask_login import login_required, current_user
from app.forms import TaskForm, FlashcardForm, StudyPlanForm

# Blueprint: Groups related routes together
main = Blueprint('main', __name__)

# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

def sync_unsynced_tasks_to_calendar(user):
    """
    Sync all existing tasks (with due dates) that aren't synced to Google Calendar.
    Returns tuple: (success_count, total_count)
    """
    service = get_calendar_service(user)
    if not service:
        return (0, 0)
    
    # Get all unsynced tasks with due dates
    unsynced_tasks = Task.query.filter_by(
        user_id=user.id,
        synced_to_calendar=False
    ).filter(Task.due_date.isnot(None)).all()
    
    success_count = 0
    total_count = len(unsynced_tasks)
    
    for task in unsynced_tasks:
        event_id = create_calendar_event(service, task)
        if event_id:
            task.google_event_id = event_id
            task.synced_to_calendar = True
            success_count += 1
    
    # Commit all changes at once
    if success_count > 0:
        db.session.commit()
    
    return (success_count, total_count)


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
    """Dashboard - overview of tasks and stats"""

    # Existing code for tasks
    tasks = Task.query.filter_by(user_id=current_user.id).all()

    # Count tasks by status
    todo_count = sum(1 for task in tasks if task.status == 'todo')
    doing_count = sum(1 for task in tasks if task.status == 'doing')
    done_count = sum(1 for task in tasks if task.status == 'done')

    # Get recent tasks
    recent_tasks = Task.query.filter_by(user_id=current_user.id).order_by(
        Task.data_created.desc()
    ).limit(5).all()

    # NEW: Get study statistics
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=7)

    # Today's study time
    today_minutes = db.session.query(db.func.sum(StudySession.duration_minutes)).filter(
        StudySession.user_id == current_user.id,
        StudySession.start_time >= today_start
    ).scalar() or 0

    # This week's study time
    week_minutes = db.session.query(db.func.sum(StudySession.duration_minutes)).filter(
        StudySession.user_id == current_user.id,
        StudySession.start_time >= week_start
    ).scalar() or 0

    # Pomodoros completed today
    pomodoros_today = PomodoroSession.query.filter(
        PomodoroSession.user_id == current_user.id,
        PomodoroSession.start_time >= today_start,
        PomodoroSession.completed == True
    ).count()

    return render_template(
        'dashboard.html',
        title='Dashboard',
        tasks=tasks,
        todo_count=todo_count,
        doing_count=doing_count,
        done_count=done_count,
        recent_tasks=recent_tasks,
        # NEW: Pass study stats
        today_minutes=today_minutes,
        week_minutes=week_minutes,
        pomodoros_today=pomodoros_today
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
    # Query the last 3 sessions for this user
    recent_sessions = PomodoroSession.query\
        .filter_by(user_id=current_user.id)\
        .order_by(PomodoroSession.created_at.desc())\
        .limit(3)\
        .all()
    
    return render_template('pomodoro.html', recent_sessions=recent_sessions, title="Pomodoro Timer")

@main.route('/my-pomodoro-sessions')
@login_required
def my_pomodoro_sessions():
    # Get page number from query params (default to 1)
    page = request.args.get('page', 1, type=int)
    per_page = 30
    
    # Paginated query
    pagination = PomodoroSession.query\
        .filter_by(user_id=current_user.id)\
        .order_by(PomodoroSession.created_at.desc())\
        .paginate(page=page, per_page=per_page, error_out=False)
    
    sessions = pagination.items
    
    # Calculate stats from ALL sessions (not just current page)
    all_sessions = PomodoroSession.query.filter_by(user_id=current_user.id).all()
    total_sessions = len(all_sessions)
    completed_sessions = len([s for s in all_sessions if s.completed])
    total_minutes = sum([s.duration_minutes for s in all_sessions if s.completed])
    
    return render_template('my_pomodoro_sessions.html', 
                         sessions=sessions,
                         pagination=pagination,
                         total_sessions=total_sessions,
                         completed_sessions=completed_sessions,
                         total_minutes=total_minutes,
                         title="My Pomodoro Sessions")

@main.route('/api/pomodoro/delete/<int:session_id>', methods=['DELETE'])
@login_required
def delete_pomodoro_session(session_id):
    """Delete a pomodoro session"""
    session = PomodoroSession.query.get_or_404(session_id)
    
    # Security check: ensure session belongs to current user
    if session.user_id != current_user.id:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    try:
        db.session.delete(session)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Session deleted successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    


@main.route('/api/pomodoro/complete', methods=['POST'])
@login_required
def api_complete_pomodoro():
    """
    API endpoint to save completed Pomodoro session
    Called from JavaScript when timer finishes
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400

        # Extract data
        duration = data.get('duration', 25)
        task_id = data.get('task_id')  # Optional
        completed = data.get('completed', True)

        # Create Pomodoro session
        pomodoro = PomodoroSession(
            user_id=current_user.id,
            task_id=task_id if task_id else None,
            duration_minutes=duration,
            break_duration_minutes=5,
            start_time=datetime.utcnow() - timedelta(minutes=duration),  # Estimate start time
            end_time=datetime.utcnow(),
            completed=completed
        )
        db.session.add(pomodoro)

        # Create corresponding study session
        study_session = StudySession(
            user_id=current_user.id,
            task_id=task_id if task_id else None,
            start_time=pomodoro.start_time,
            end_time=pomodoro.end_time,
            duration_minutes=duration
        )
        db.session.add(study_session)
        db.session.flush()  # Get IDs

        # Link them
        pomodoro.study_session_id = study_session.id

        # Update task's actual time
        if task_id:
            task = Task.query.get(task_id)
            if task and task.user_id == current_user.id:
                task.actual_minutes = (task.actual_minutes or 0) + duration

        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Pomodoro session saved!',
            'session_id': pomodoro.id,
            'total_minutes_today': get_today_study_minutes(current_user.id)
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


def get_today_study_minutes(user_id):
    """Helper function to get total study minutes for today"""
    from datetime import datetime, timedelta

    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    total = db.session.query(db.func.sum(StudySession.duration_minutes)).filter(
        StudySession.user_id == user_id,
        StudySession.start_time >= today_start
    ).scalar()

    return total or 0


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


@main.route("/generate_flashcards_from_study_plan/<int:plan_id>", methods=["POST"])
@login_required
def generate_flashcards_from_study_plan(plan_id):
    """Generate flashcards from a study plan using AI"""
    # Get the study plan
    plan = StudyPlan.query.get_or_404(plan_id)
    
    # Security check - verify user owns this plan
    if plan.user_id != current_user.id:
        flash('You are not authorized to access this plan.', 'danger')
        return redirect(url_for('main.my_study_plans'))
    
    # Get number of cards from form
    num_cards = int(request.form.get('num_cards', 10))
    
    try:
        # Use Gemini AI to generate flashcards from the study plan
        from google import genai
        import os
        
        api_key = os.getenv('GEMINI_API_KEY', 'AIzaSyCbDUdL0WUWP20lS4rZM4bqGBSmUqoj54o')
        client = genai.Client(api_key=api_key)
        
        prompt = f"""Based on the following study plan for {plan.subject}, generate {num_cards} flashcards 
to help the student review key concepts. Each flashcard should have a clear question and a concise answer.

Study Plan:
{plan.plan_content}

Generate exactly {num_cards} flashcards in the following format:
Q: [Question]
A: [Answer]

Make the questions specific and the answers clear and educational."""
        
        response = client.models.generate_content(
            model='gemini-flash-latest',
            contents=prompt
        )
        
        # Parse the response to extract Q&A pairs
        flashcard_text = response.text
        lines = flashcard_text.strip().split('\n')
        
        question = None
        cards_added = 0
        
        for line in lines:
            line = line.strip()
            if line.startswith('Q:'):
                question = line[2:].strip()
            elif line.startswith('A:') and question:
                answer = line[2:].strip()
                # Create and save the flashcard
                new_flashcard = Flashcard(
                    question=question,
                    answer=answer,
                    author=current_user
                )
                db.session.add(new_flashcard)
                cards_added += 1
                question = None
        
        db.session.commit()
        flash(f'Successfully generated {cards_added} flashcards from your study plan!', 'success')
        
    except Exception as e:
        current_app.logger.error(f"Error generating flashcards: {str(e)}")
        flash(f'Error generating flashcards: {str(e)}', 'danger')
    
    return redirect(url_for('main.flashcards'))

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
    
    # Check if user has existing tasks with due dates that could be synced
    unsynced_count = Task.query.filter_by(
        user_id=current_user.id,
        synced_to_calendar=False
    ).filter(Task.due_date.isnot(None)).count()
    
    if unsynced_count > 0:
        # Redirect to sync prompt
        return redirect(url_for('main.calendar_sync_prompt', count=unsynced_count))
    else:
        # No tasks to sync, go directly to schedule
        return redirect(url_for('main.schedule'))

@main.route('/calendar_sync_prompt')
@login_required
def calendar_sync_prompt():
    """
    Show prompt asking user if they want to sync existing tasks to Google Calendar.
    This is shown after first connecting Google Calendar.
    """
    count = request.args.get('count', 0, type=int)
    
    if not current_user.calendar_sync_enabled:
        flash('Please connect Google Calendar first.', 'warning')
        return redirect(url_for('main.schedule'))
    
    return render_template('calendar_sync_prompt.html', 
                         title='Sync Tasks to Calendar',
                         count=count)

@main.route('/sync_existing_tasks', methods=['POST'])
@login_required
def sync_existing_tasks():
    """
    Sync all existing unsynced tasks to Google Calendar.
    Called when user clicks 'Yes, Sync All' on the prompt.
    """
    if not current_user.calendar_sync_enabled:
        flash('Google Calendar not connected.', 'danger')
        return redirect(url_for('main.schedule'))
    
    success_count, total_count = sync_unsynced_tasks_to_calendar(current_user)
    
    if success_count == total_count:
        flash(f'Successfully synced {success_count} tasks to Google Calendar!', 'success')
    elif success_count > 0:
        flash(f'Synced {success_count} out of {total_count} tasks. Some tasks may have failed.', 'warning')
    else:
        flash('Failed to sync tasks to Google Calendar.', 'danger')
    
    return redirect(url_for('main.schedule'))

@main.route('/skip_sync_existing_tasks', methods=['POST'])
@login_required
def skip_sync_existing_tasks():
    """
    Skip syncing existing tasks. Only new tasks will auto-sync.
    """
    flash('Only new tasks will be synced to Google Calendar.', 'info')
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
    Simplified schedule page - just renders HTML skeleton.
    JavaScript will fetch all data via AJAX.
    """
    from datetime import datetime

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
        'schedule.html',
        title='Schedule',
        calendar_connected=calendar_connected,
        target_date=target_date,
        view=view_param,
        current_month=target_date.strftime('%B, %Y')
    )

@main.route('/api/calendar/events')
@login_required
def api_calendar_events():
    """
    UNIFIED API endpoint to get ALL calendar data for any date range.
    Returns JSON instead of HTML.
    """
    from datetime import datetime, timedelta
    from calendar import monthrange

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
                from app.google_calendar import get_events_for_date_range
                calendar_events = get_events_for_date_range(service, start_date, end_date)
                calendar_connected = True
            except Exception as e:
                print(f"Error fetching calendar events: {e}")
                calendar_connected = False

    # Fetch local tasks for the date range
    tasks = Task.query.filter(
        Task.user_id == current_user.id,
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


# ==============================================================================
# AI STUDY PLAN GENERATOR ROUTES
# ==============================================================================

@main.route('/ai-plan-generator', methods=['GET', 'POST'])
@login_required
def ai_plan_generator():
    """AI-powered study plan generator page"""
    form = StudyPlanForm()
    
    if form.validate_on_submit():
        try:
            # Generate the study plan using AI
            plan_content = generate_study_plan(
                subject=form.subject.data,
                days_until_exam=form.days_until_exam.data,
                hours_per_day=form.hours_per_day.data,
                knowledge_level=form.knowledge_level.data
            )
            
            # Save the plan to database
            study_plan = StudyPlan(
                user_id=current_user.id,
                subject=form.subject.data,
                days_until_exam=form.days_until_exam.data,
                hours_per_day=form.hours_per_day.data,
                knowledge_level=form.knowledge_level.data,
                plan_content=plan_content
            )
            
            db.session.add(study_plan)
            db.session.commit()
            
            flash('Study plan generated successfully!', 'success')
            return redirect(url_for('main.view_study_plan', plan_id=study_plan.id))
            
        except Exception as e:
            flash(f'Error generating study plan: {str(e)}', 'danger')
            current_app.logger.error(f"AI Plan Generation Error: {str(e)}")
    
    # Get user's previous plans
    previous_plans = StudyPlan.query.filter_by(user_id=current_user.id)\
        .order_by(StudyPlan.created_at.desc()).limit(5).all()
    
    return render_template(
        'ai_plan_generator.html',
        title='AI Study Plan Generator',
        form=form,
        previous_plans=previous_plans
    )


@main.route('/view-study-plan/<int:plan_id>')
@login_required
def view_study_plan(plan_id):
    """View a specific study plan"""
    plan = StudyPlan.query.get_or_404(plan_id)
    
    # Security check - verify user owns this plan
    if plan.user_id != current_user.id:
        flash('You are not authorized to view this plan.', 'danger')
        return redirect(url_for('main.ai_plan_generator'))
    
    # Format the plan content for display
    formatted_content = format_plan_for_display(plan.plan_content)
    
    return render_template(
        'view_study_plan.html',
        title=f'Study Plan: {plan.subject}',
        plan=plan,
        formatted_content=formatted_content
    )


@main.route('/my-study-plans')
@login_required
def my_study_plans():
    """View all user's study plans"""
    plans = StudyPlan.query.filter_by(user_id=current_user.id)\
        .order_by(StudyPlan.created_at.desc()).all()
    
    return render_template(
        'my_study_plans.html',
        title='My Study Plans',
        plans=plans
    )


@main.route('/delete-study-plan/<int:plan_id>', methods=['POST'])
@login_required
def delete_study_plan(plan_id):
    """Delete a study plan"""
    plan = StudyPlan.query.get_or_404(plan_id)
    
    # Security check - verify user owns this plan
    if plan.user_id != current_user.id:
        flash('You are not authorized to delete this plan.', 'danger')
        return redirect(url_for('main.ai_plan_generator'))
    
    db.session.delete(plan)
    db.session.commit()
    flash('Study plan deleted successfully!', 'success')
    return redirect(url_for('main.ai_plan_generator'))
