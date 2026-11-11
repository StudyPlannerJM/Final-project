"""Navigation state shared by the sidebar and the mobile bottom tab bar."""

from flask import request

# blueprint -> (sidebar/sheet item, bottom tab)
_BLUEPRINT_NAV = {
    'tasks': ('tasks', 'tasks'),
    'calendar': ('schedule', 'schedule'),
    'pomodoro': ('pomodoro', 'study'),
    'flashcards': ('flashcards', 'study'),
    'summarizer': ('summarizer', 'more'),
    'ai_planner': ('ai_planner', 'more'),
    'admin': ('admin', 'more'),
}


def nav_state(blueprint, endpoint):
    """Return which nav item and which bottom tab are active for a request.

    Both values are None for pages that belong to no section (auth, errors).
    """
    if blueprint == 'main':
        if endpoint == 'main.settings':
            return {'item': 'settings', 'tab': 'more'}
        return {'item': 'dashboard', 'tab': 'home'}
    item, tab = _BLUEPRINT_NAV.get(blueprint, (None, None))
    return {'item': item, 'tab': tab}


def user_initial(username):
    """First visible character of a username, upper-cased; '?' if there is none."""
    stripped = (username or '').strip()
    return stripped[0].upper() if stripped else '?'


def register_navigation(app):
    """Expose `nav` and `user_initial` to every template."""

    @app.context_processor
    def inject_navigation():
        return {
            'nav': nav_state(request.blueprint, request.endpoint),
            'user_initial': user_initial,
        }
