"""
Pomodoro Blueprint - Pomodoro timer and session management routes
"""
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from app.models import PomodoroSession, StudySession, Task
from app import db
from app.decorators import require_resource_ownership
pomodoro_bp = Blueprint('pomodoro', __name__, url_prefix='/pomodoro')


@pomodoro_bp.route('/')
@login_required
def index():
    """Pomodoro timer page"""
    # Query the last 3 sessions for this user
    recent_sessions = PomodoroSession.query\
        .filter_by(user_id=current_user.id)\
        .order_by(PomodoroSession.created_at.desc())\
        .limit(3)\
        .all()
    
    return render_template('pomodoro/pomodoro.html', recent_sessions=recent_sessions, title="Pomodoro Timer")


@pomodoro_bp.route('/sessions')
@login_required
def sessions():
    """View all pomodoro sessions"""
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
    
    return render_template('pomodoro/my_pomodoro_sessions.html', 
                         sessions=sessions,
                         pagination=pagination,
                         total_sessions=total_sessions,
                         completed_sessions=completed_sessions,
                         total_minutes=total_minutes,
                         title="My Pomodoro Sessions")


@pomodoro_bp.route('/api/delete/<int:session_id>', methods=['DELETE'])
@login_required
@require_resource_ownership(PomodoroSession, id_param='session_id')
def delete_session(session_id):
    """Delete a pomodoro session"""
    session = PomodoroSession.query.get_or_404(session_id)
    
    try:
        db.session.delete(session)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Session deleted successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@pomodoro_bp.route('/api/complete', methods=['POST'])
@login_required
def api_complete():
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
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    total = db.session.query(db.func.sum(StudySession.duration_minutes)).filter(
        StudySession.user_id == user_id,
        StudySession.start_time >= today_start
    ).scalar()

    return total or 0
