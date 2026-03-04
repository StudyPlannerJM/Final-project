"""
Utility modules for the BrainDump application
"""
from .ai_generator import generate_study_plan, format_plan_for_display
from .document_processor import (
    get_allowed_extensions,
    get_file_type,
    extract_text,
    generate_summary
)
from .calendar_client import (
    get_google_auth_flow,
    get_calendar_service,
    create_calendar_event,
    update_calendar_event,
    delete_calendar_event,
    get_events_for_date_range,
    get_week_events,
    sync_unsynced_tasks_to_calendar
)

__all__ = [
    'generate_study_plan',
    'format_plan_for_display',
    'get_allowed_extensions',
    'get_file_type',
    'extract_text',
    'generate_summary',
    'get_google_auth_flow',
    'get_calendar_service',
    'create_calendar_event',
    'update_calendar_event',
    'delete_calendar_event',
    'get_events_for_date_range',
    'get_week_events',
    'sync_unsynced_tasks_to_calendar',
]
