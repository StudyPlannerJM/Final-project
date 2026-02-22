"""
Routes package - Blueprint modules for organized routing
"""
from .main import main_bp
from .tasks import tasks_bp
from .flashcards import flashcards_bp
from .pomodoro import pomodoro_bp
from .calendar_routes import calendar_bp
from .summarizer import summarizer_bp
from .ai_planner import ai_planner_bp

__all__ = [
    'main_bp',
    'tasks_bp',
    'flashcards_bp',
    'pomodoro_bp',
    'calendar_bp',
    'summarizer_bp',
    'ai_planner_bp'
]
