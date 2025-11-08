#type: ignore
from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.models import Task, User
from app import db
from datetime import datetime
from flask_login import current_user, login_required

main = Blueprint('main', __name__)

@main.route('/')
@main.route('/dashboard')
@login_required
def dashboard():
    tasks = Task.query.filter_by(author=current_user).order_by
    (Task.due_date.asc()).all()
    return render_template('dashboard.html', title='Dashboard', tasks=tasks)

@main.route('/add_task', methods=['GET', 'POST'])
@login_required
def add_task():
    if request.method == 'POST':
        # ...
        new_task = Task(title=title, description=request.form.get('description'), author=current_user)
        # ...
    return render_template('add_task.html', title='Add New Task')

@main.route('/edit_task/<int:task_id>', methods=['GET', 'POST'])
@login_required
def edit_task(task_id):
    task = Task.query.get_or_404(task_id)
    if task.author != current_user:
        flash('You are not authorized to edit this task.', 'danger')
        return redirect(url_for('main.dashboard'))
    # ...

@main.route('/delete_task/<int:task_id>', methods=['POST'])
@login_required
def delete_task(task_id):
    task = Task.query.get_or_404(task_id)
    if task.author != current_user:
        flash('You are not authorized to delete this task.', 'danger')
        return redirect(url_for('main.dashboard'))
    # ...

@main.route('/complete_task/<int:task_id>', methods=['POST'])
@login_required
def complete_task(task_id):
    task = Task.query.get_or_404(task_id)
    if task.author != current_user:
        flash('You are not authorized to complete this task.', 'danger')
        return redirect(url_for('main.dashboard'))
    # ...

@main.route('/settings')
@login_required
def settings():
    return render_template('settings.html', title='Settings')