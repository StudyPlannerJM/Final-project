from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.models import Task, User
from app import db
from datetime import datetime

main = Blueprint('main', __name__)

@main.route('/')
@main.route('/dashboard')
def dashboard():
    user_id = 1  # Placeholder for the logged-in user ID
    tasks = Task.query.filter_by(user_id=user_id).order_by(Task.due_date.asc).all()
    return render_template('dashboard.html', title='Dashboard', tasks=tasks)

@main.route('/add_task', methods=['GET', 'POST'])
def add_task():
    if request.method == 'POST':
        title = request.form.get('title')
        if not title:
            flash('Task title is required!', 'danger')
            return redirect(url_for('main.add_task'))
        new_task = Task(title=title, description=request.form.get('description'), user_id=1)
        db.session.add(new_task)
        db.session.commit()
        flash('Task added successfully!', 'success')
        return redirect(url_for('main.dashboard'))
    return render_template('add_task.html', title='Add New Task')

@main.route('/complete_task/<int:task_id>', methods=['POST'])
def complete_task(task_id):
    task = Task.query.get_or_404(task_id)
    if task.user_id != 1: # Simple authorization check
        flash('You are not authorized to complete this task.', 'danger')
        return redirect(url_for('main.dashboard'))
    task.is_complete = not task.is_complete
    db.session.commit()
    flash('Task status updated!', 'success')
    return redirect(url_for('main.dashboard'))