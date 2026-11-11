from flask import Blueprint, render_template, redirect, url_for, flash, current_app, request
from app import db
from app.forms import LoginForm, RegistrationForm
from app.models import User
from app.services.login_limiter import LoginLimiter
from urllib.parse import urlsplit
from flask_login import login_user, logout_user, current_user
from sqlalchemy.exc import SQLAlchemyError

auth_bp = Blueprint('auth', __name__)


def _safe_next(target):
    """Return target only if it is a path on this site; otherwise None (no open redirects)."""
    if not target or not target.startswith('/') or target.startswith('//') or '\\' in target:
        return None
    parts = urlsplit(target)
    if parts.scheme or parts.netloc:
        return None
    return target

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    form = LoginForm()  
     
    if form.validate_on_submit():
        email = form.email.data or ''
        ip = request.remote_addr or ''

        wait = LoginLimiter.seconds_until_allowed(email, ip)
        if wait:
            minutes = max(1, -(-wait // 60))
            flash(f'Too many sign-in attempts. Try again in {minutes} minute'
                  f'{"" if minutes == 1 else "s"}.', 'danger')
            current_app.logger.warning(
                'Sign-in blocked by rate limit (remote_addr=%s, X-Forwarded-For=%s)',
                ip, request.headers.get('X-Forwarded-For', ''))
            return render_template('auth/login.html', title='Sign In', form=form), 429

        try:
            user = User.query.filter_by(email=email).first()
        except SQLAlchemyError as exc:
            db.session.rollback()
            current_app.logger.exception("Login query failed due to DB error: %s", exc)
            flash('Login temporarily unavailable. Please try again shortly.', 'danger')
            return redirect(url_for('auth.login', next=request.args.get('next') or None))

        if user is None or not user.check_password(form.password.data):
            LoginLimiter.record_failure(email, ip)
            flash('Invalid email or password', 'danger')
            return redirect(url_for('auth.login', next=request.args.get('next') or None))

        LoginLimiter.clear(email)
        login_user(user, remember=form.remember_me.data)
        current_app.logger.info(f"Login successful for user: {user.username}")
        return redirect(_safe_next(request.args.get('next')) or url_for('main.dashboard'))
    return render_template('auth/login.html', title='Sign In', form=form)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    form = RegistrationForm()
    if form.validate_on_submit():
        try:
            user = User(username=form.username.data, email=form.email.data)  # type: ignore
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()
        except SQLAlchemyError as exc:
            db.session.rollback()
            current_app.logger.exception("Registration failed due to DB error: %s", exc)
            flash('Registration temporarily unavailable. Please try again.', 'danger')
            return redirect(url_for('auth.register'))
        flash('Congratulations, you are now a registered user!', 'success')
        return redirect(url_for('auth.login'))
    return render_template('auth/register.html', title='Register', form=form)

@auth_bp.route('/logout', methods=['GET', 'POST'])
def logout():
    # Signing out changes state, so it needs a POST (with its CSRF token).
    # A plain link or another site's <img src> must not sign anyone out.
    if request.method == 'GET':
        return redirect(url_for('main.dashboard') if current_user.is_authenticated else url_for('auth.login'))
    logout_user()
    flash('You have been logged out.', 'info')   
    return redirect(url_for('auth.login'))
    