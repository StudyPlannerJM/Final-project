"""
Main Blueprint - Dashboard and general routes
"""
from flask import Blueprint, current_app, render_template, send_from_directory
from flask_login import login_required, current_user
from app import db
from app.models import Task, Deck, Flashcard
from app.services.review_service import ReviewService
from app.services.stats_service import StatsService
from app.utils.timezone import get_user_timezone, local_now

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
@main_bp.route('/dashboard')
@login_required
def dashboard():
    """Dashboard - what to do today, study progress and overview counts"""
    user_id = current_user.id

    # "Today" is the user's own calendar day (timezone comes from a cookie)
    tz = get_user_timezone()
    now_local = local_now(tz)
    today = now_local.date()

    # Task counts by status (one grouped query)
    status_counts = dict(
        db.session.query(Task.status, db.func.count(Task.id))
        .filter(Task.user_id == user_id)
        .group_by(Task.status)
        .all()
    )

    recent_tasks = Task.query.filter_by(user_id=user_id).order_by(
        Task.date_created.desc()
    ).limit(5).all()

    # Study time
    week = StatsService.weekly_minutes(user_id, tz, today)
    today_minutes = week[-1]['minutes']
    week_minutes = sum(day['minutes'] for day in week)

    return render_template(
        'dashboard.html',
        title='Dashboard',
        todo_count=status_counts.get('todo', 0),
        doing_count=status_counts.get('doing', 0),
        done_count=status_counts.get('done', 0),
        recent_tasks=recent_tasks,
        today_minutes=today_minutes,
        week_minutes=week_minutes,
        pomodoros_today=StatsService.pomodoros_on(user_id, tz, today),
        total_decks=Deck.query.filter_by(user_id=user_id).count(),
        total_flashcards=Flashcard.query.filter_by(user_id=user_id).count(),
        # Phase 3 panels
        today_tasks=StatsService.today_tasks(user_id, now_local),
        cards_due=ReviewService.count_due(user_id),
        streak=StatsService.streak(user_id, tz, today),
        week=week,
        deck_progress=ReviewService.deck_progress(user_id),
    )


@main_bp.route('/settings')
@login_required
def settings():
    """User settings page"""
    return render_template('settings.html', title='Settings')


# ==============================================================================
# INSTALLABLE APP (PWA)
# ==============================================================================

@main_bp.route('/sw.js')
def service_worker():
    """
    Serve the service worker from the site root so its scope is the whole app.
    Public on purpose: the browser fetches it without credentials on install.
    """
    response = send_from_directory(
        current_app.static_folder, 'js/sw.js', mimetype='text/javascript', max_age=0
    )
    response.headers['Cache-Control'] = 'no-cache'
    return response


@main_bp.route('/offline')
def offline():
    """Fallback page shown by the service worker when there is no connection."""
    return render_template('offline.html')
