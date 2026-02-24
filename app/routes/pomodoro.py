"""
Pomodoro Blueprint - Pomodoro timer and session management routes
"""
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from app.models import PomodoroSession
from app.services import PomodoroService
from app.decorators import require_resource_ownership
from app.exceptions import ValidationError, AuthorizationError, NotFoundError
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
    
    # Calculate stats using service
    stats = PomodoroService.get_user_statistics(current_user.id)
    
    return render_template('pomodoro/my_pomodoro_sessions.html', 
                         sessions=sessions,
                         pagination=pagination,
                         total_sessions=stats['total_sessions'],
                         completed_sessions=stats['completed_sessions'],
                         total_minutes=stats['total_minutes'],
                         title="My Pomodoro Sessions")


@pomodoro_bp.route('/api/delete/<int:session_id>', methods=['DELETE'])
@login_required
@require_resource_ownership(PomodoroSession, id_param='session_id')
def delete_session(session_id):
    """Delete a pomodoro session"""
    try:
        PomodoroService.delete_session(session_id, current_user.id)
        return jsonify({'success': True, 'message': 'Session deleted successfully'})
    except (NotFoundError, AuthorizationError) as e:
        return jsonify({'success': False, 'error': str(e)}), 403
    except Exception as e:
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

        # Create session using service
        pomodoro, total_minutes_today = PomodoroService.create_session(
            user_id=current_user.id,
            duration=duration,
            task_id=task_id,
            completed=completed
        )

        return jsonify({
            'success': True,
            'message': 'Pomodoro session saved!',
            'session_id': pomodoro.id,
            'total_minutes_today': total_minutes_today
        })

    except ValidationError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except (NotFoundError, AuthorizationError) as e:
        return jsonify({'success': False, 'error': str(e)}), 403
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
