"""Quick script to delete incorrect Pomodoro sessions"""
import sys
sys.path.insert(0, '.')

from app import create_app, db
from app.models import PomodoroSession, StudySession

app = create_app()

with app.app_context():
    # Delete the incorrect 51-minute sessions
    wrong_pomodoros = PomodoroSession.query.filter_by(duration_minutes=51).all()
    for session in wrong_pomodoros:
        print(f"Deleting Pomodoro session: {session.id} ({session.duration_minutes} min)")
        db.session.delete(session)
    
    wrong_studies = StudySession.query.filter_by(duration_minutes=51).all()
    for session in wrong_studies:
        print(f"Deleting Study session: {session.id} ({session.duration_minutes} min)")
        db.session.delete(session)
    
    db.session.commit()
    print("\n✅ Database cleaned! Incorrect sessions removed.")
    
    # Show remaining sessions
    remaining = PomodoroSession.query.all()
    print(f"\nRemaining Pomodoro sessions: {len(remaining)}")
    for session in remaining:
        print(f"  - {session.duration_minutes} minutes")
