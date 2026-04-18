from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    url_for,
)
from app import db
from app.forms import LoginForm, RegistrationForm
from app.models import User
from flask_login import login_user, logout_user, current_user
from sqlalchemy.exc import SQLAlchemyError

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    form = LoginForm()

    if form.validate_on_submit():
        try:
            user = User.query.filter_by(email=form.email.data).first()
        except SQLAlchemyError as exc:
            db.session.rollback()
            current_app.logger.exception(
                "Login query failed due to DB error: %s",
                exc,
            )
            flash(
                'Login temporarily unavailable. Please try again shortly.',
                'danger',
            )
            return redirect(url_for('auth.login'))

        if user is None or not user.check_password(form.password.data):
            flash('Invalid email or password', 'danger')
            return redirect(url_for('auth.login'))

        current_app.logger.info(f"User login attempt: {user.username}")
        login_user(user, remember=form.remember_me.data)
        current_app.logger.info(f"Login successful for user: {user.username}")

        return redirect(url_for('main.dashboard'))

    return render_template('auth/login.html', title='Sign In', form=form)


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    form = RegistrationForm()
    if form.validate_on_submit():
        try:
            user = User(
                username=form.username.data,
                email=form.email.data,
            )  # type: ignore
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()
        except SQLAlchemyError as exc:
            db.session.rollback()
            current_app.logger.exception(
                "Registration failed due to DB error: %s",
                exc,
            )
            flash(
                'Registration temporarily unavailable. Please try again.',
                'danger',
            )
            return redirect(url_for('auth.register'))

        flash('Congratulations, you are now a registered user!', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html', title='Register', form=form)


@auth_bp.route('/logout')
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))
