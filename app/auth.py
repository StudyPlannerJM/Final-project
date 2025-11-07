from flask import Blueprint, render_template, redirect, url_for, flash


auth = Blueprint('auth', __name__)

@auth.route('/login')
def login():
    return render_template('auth/login.html')

@auth.route('/register')
def register():
    return render_template('auth/register.html')

@auth.route('/logout')
def logout():
    return redirect(url_for('main.dashboard')) # Placeholder