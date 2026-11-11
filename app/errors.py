"""
Error responses: friendly pages for people, JSON for scripts.

Every page works signed in or out and does not depend on the app shell,
so it can render even when something else on the request has failed.
"""

from flask import current_app, flash, jsonify, redirect, render_template, request, url_for
from flask_wtf.csrf import CSRFError

from app import db

# code: (title, message, offer "Go back")
ERRORS = {
    400: ('Something was wrong with that request',
          'Go back, reload the page and try again.', True),
    403: ("You don't have access",
          "This page belongs to another account or needs permissions you don't have.", True),
    404: ('Page not found',
          "We couldn't find that page. It may have been moved or deleted.", False),
    405: ('That action is not available',
          'That link cannot be used this way. Use the button on the page instead.', True),
    429: ('Too many attempts',
          'Please wait a little and try again.', True),
    500: ('Something went wrong',
          'Sorry, something broke on our side. Please try again in a moment.', True),
}

SESSION_EXPIRED = ('Session expired',
                   'This page was open for too long or your session changed. '
                   'Go back, reload the page and try again.')


def wants_json():
    """True for fetch/XHR calls that expect JSON rather than a page."""
    if request.is_json:
        return True
    # fetch()/XHR requests are not page loads; browsers mark navigations as "document"
    if request.headers.get('Sec-Fetch-Dest') == 'empty':
        return True
    accept = request.accept_mimetypes
    best = accept.best_match(['application/json', 'text/html'])
    return best == 'application/json' and accept[best] > accept['text/html']


def error_response(code, message=None, title=None):
    default_title, default_message, show_back = ERRORS.get(code, ERRORS[500])
    title = title or default_title
    message = message or default_message
    if wants_json():
        return jsonify({'success': False, 'error': message}), code
    return render_template('errors/error.html', code=code, title=title,
                           message=message, show_back=show_back), code


def register_error_handlers(app):
    @app.errorhandler(CSRFError)
    def csrf_error(error):
        # A sign-in or registration page restored from an old tab: start it afresh
        if request.endpoint in ('auth.login', 'auth.register') and not wants_json():
            flash('That page had expired. Please try again.', 'warning')
            return redirect(url_for(request.endpoint, **request.args))
        if wants_json():
            return error_response(400, 'Your session has expired. Reload the page and try again.')
        return error_response(400, SESSION_EXPIRED[1], SESSION_EXPIRED[0])

    for code in (400, 403, 404, 405, 429):
        app.register_error_handler(code, lambda error, code=code: error_response(code))

    @app.errorhandler(500)
    def server_error(error):
        # Leave the database usable for the next request (Flask has already logged the error)
        try:
            db.session.rollback()
        except Exception:
            current_app.logger.warning('Could not roll back the database session after an error')
        try:
            return error_response(500)
        except Exception:  # the error page itself failed: fall back to plain text
            return 'Something went wrong. Please try again in a moment.', 500
