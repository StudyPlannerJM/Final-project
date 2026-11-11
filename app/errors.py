"""
Error responses: friendly pages for people, JSON for scripts.

Every page works signed in or out and does not depend on the app shell,
so it can render even when something else on the request has failed.
"""

from flask import jsonify, render_template, request
from flask_wtf.csrf import CSRFError

ERRORS = {
    400: ('Session expired', 'This page was open for too long or your session changed. '
                             'Go back, reload the page and try again.', True),
    403: ("You don't have access", "This page belongs to another account or needs permissions you don't have.", True),
    404: ('Page not found', "We couldn't find that page. It may have been moved or deleted.", False),
    405: ('That action is not available', 'That link cannot be used this way. Use the button on the page instead.', True),
    429: ('Too many attempts', 'Please wait a little and try again.', True),
    500: ('Something went wrong', 'Sorry, something broke on our side. Please try again in a moment.', True),
}


def wants_json():
    """True for fetch/XHR calls that expect JSON rather than a page."""
    if request.is_json:
        return True
    best = request.accept_mimetypes.best_match(['application/json', 'text/html'])
    return best == 'application/json' and request.accept_mimetypes[best] > request.accept_mimetypes['text/html']


def error_response(code, message=None):
    title, default_message, show_back = ERRORS.get(code, ERRORS[500])
    message = message or default_message
    if wants_json():
        return jsonify({'success': False, 'error': message}), code
    return render_template('errors/error.html', code=code, title=title,
                           message=message, show_back=show_back), code


def register_error_handlers(app):
    @app.errorhandler(CSRFError)
    def csrf_error(error):
        return error_response(400, 'Your session has expired. Reload the page and try again.'
                              if wants_json() else None)
