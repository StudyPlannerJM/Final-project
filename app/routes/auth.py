from flask import Blueprint, render_template, redirect, url_for, flash, current_app
from app import db
from app.forms import LoginForm, RegistrationForm
from app.models import User
from flask_login import login_user, logout_user, current_user

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    form = LoginForm()  
     
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
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
        user = User(username=form.username.data, email=form.email.data) #type: ignore
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Congratulations, you are now a registered user!', 'success')
        return redirect(url_for('auth.login'))
    return render_template('auth/register.html', title='Register', form=form)

@auth_bp.route('/logout')
def logout():    
    logout_user() 
    flash('You have been logged out.', 'info')   
    return redirect(url_for('auth.login'))
    