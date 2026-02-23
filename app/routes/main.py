"""
Main Blueprint - Dashboard and general routes
"""
from datetime import datetime, timedelta, timezone
from flask import Blueprint, render_template
from flask_login import login_required, current_user
from app.models import Task, StudySession, PomodoroSession, Deck, Flashcard
from app import db

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
@main_bp.route('/dashboard')
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
        Task.date_created.desc()
    ).limit(5).all()

    # NEW: Get study statistics
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
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
        PomodoroSession.completed.is_(True)
    ).count()

    # Deck and Flashcard statistics
    total_decks = Deck.query.filter_by(user_id=current_user.id).count()
    total_flashcards = Flashcard.query.filter_by(user_id=current_user.id).count()

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
        pomodoros_today=pomodoros_today,
        # Flashcard stats
        total_decks=total_decks,
        total_flashcards=total_flashcards
    )


@main_bp.route('/settings')
@login_required
def settings():
    """User settings page"""
    return render_template('settings.html', title='Settings')
