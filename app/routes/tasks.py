"""
Tasks Blueprint - Task management routes
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models import Task, Category
from app.forms import TaskForm
from app import db
from app.decorators import require_resource_ownership
from app.utils.calendar_client import get_calendar_service, create_calendar_event, update_calendar_event, delete_calendar_event

tasks_bp = Blueprint('tasks', __name__, url_prefix='/tasks')


@tasks_bp.route('/')
@login_required
def index():
    """Display all tasks organized by status (todo, doing, done) - Kanban board view"""
    
    # STEP 1: Get all "todo" tasks for current user, sorted by creation date
    todo_tasks = Task.query.filter_by(user_id=current_user.id, status="todo").order_by(
        Task.date_created.asc()
    ).all()
    
    # STEP 2: Get all "doing" (in progress) tasks
    doing_tasks = Task.query.filter_by(user_id=current_user.id, status="doing").order_by(
        Task.date_created.asc()
    ).all()
    
    # STEP 3: Get all "done" (completed) tasks
    done_tasks = Task.query.filter_by(user_id=current_user.id, status='done').order_by(
        Task.date_created.asc()
    ).all()
    
    # STEP 4: Pass all three lists to the template for display
    return render_template(
        'tasks/tasks.html', 
        title='Tasks', 
        todo_tasks=todo_tasks,
        doing_tasks=doing_tasks,
        done_tasks=done_tasks
    )


@tasks_bp.route('/update_status/<int:task_id>/<status>', methods=['POST'])
@login_required
@require_resource_ownership(Task, id_param='task_id')
def update_status(task_id, status):
    """Update task status when dragging between Kanban columns (AJAX endpoint)"""
    
    # STEP 1: Get the task from database (ownership already verified by decorator)
    task = Task.query.get_or_404(task_id)

    # STEP 2: Validate the new status is valid (todo, doing, or done)
    if status not in ['todo', 'doing', 'done']:
        return {'success': False, 'error': 'Invalid status'}, 400

    # STEP 3: Update the task's status and save to database
    task.status = status
    db.session.commit()

    # STEP 4: Return success response to JavaScript
    return {'success': True, 'task_id': task_id, 'new_status': status}


@tasks_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    """
    Create a new task and optionally sync to Google Calendar.
    
    Handles both predefined categories and custom user-created categories.
    If Google Calendar sync is enabled, automatically creates a calendar event.
    """
    form = TaskForm()

    if form.validate_on_submit():
        # STEP 1: Determine which category to use
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
            user_id=current_user.id,
            description=form.description.data,
            due_date=form.due_date.data,
            category_id=category_id  # Foreign key to Category table
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
        return redirect(url_for('tasks.index'))

    # GET request: Show empty form
    return render_template('tasks/add_task.html', title='Add New Task', form=form)


@tasks_bp.route('/edit/<int:task_id>', methods=['GET', 'POST'])
@login_required
@require_resource_ownership(Task, id_param='task_id')
def edit(task_id):
    """Edit an existing task - modify title, description, date, or category"""

    task = Task.query.get_or_404(task_id)

    form = TaskForm(obj=task)

    # On GET request, pre-select the category
    if request.method == "GET":
        if task.category_id:
            form.category.data = db.session.get(Category, task.category_id)

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
        elif selected_category:
            task.category_id = selected_category.id
        else:
            task.category_id = None

        db.session.commit()

        # Update Google Calendar if synced
        if current_user.calendar_sync_enabled and task.google_event_id:
            service = get_calendar_service(current_user)
            if service:
                update_calendar_event(service, task.google_event_id, task)

        flash("Your task has been updated!", "success")
        return redirect(url_for("tasks.index"))

    return render_template("tasks/edit_task.html", title="Edit Task", form=form, task=task)


@tasks_bp.route('/delete/<int:task_id>', methods=['POST'])
@login_required
@require_resource_ownership(Task, id_param='task_id')
def delete(task_id):
    """Delete a task permanently from the database"""
    task = Task.query.get_or_404(task_id)

    # Delete from Google Calendar if synced
    if task.google_event_id and current_user.calendar_sync_enabled:
        service = get_calendar_service(current_user)
        if service:
            delete_calendar_event(service, task.google_event_id)
            
    db.session.delete(task)
    db.session.commit()
    flash('Your task has been deleted!', 'success')
    return redirect(url_for('tasks.index'))


@tasks_bp.route('/complete/<int:task_id>', methods=['POST'])
@login_required
@require_resource_ownership(Task, id_param='task_id')
def complete(task_id):
    """Toggle task completion status (mark as complete/incomplete)"""
    task = Task.query.get_or_404(task_id)
    task.is_complete = not task.is_complete
    db.session.commit()
    flash('Task status updated!', 'success')
    return redirect(url_for('tasks.index'))
