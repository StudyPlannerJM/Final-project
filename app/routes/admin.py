"""
Admin Blueprint - User management for administrators
"""
from flask import Blueprint, render_template, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from app import db
from app.models import User
from app.forms import AdminCreateUserForm, AdminEditUserForm
from app.decorators import admin_required

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


@admin_bp.route('/users')
@login_required
@admin_required
def manage_users():
    """List all users"""
    users = User.query.order_by(User.username).all()
    return render_template(
        'admin/manage_users.html',
        title='Manage Users',
        users=users
    )


@admin_bp.route('/users/new', methods=['GET', 'POST'])
@login_required
@admin_required
def create_user():
    """Create a new user"""
    form = AdminCreateUserForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data, is_admin=form.is_admin.data)  # type: ignore
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash(f'User "{user.username}" has been created successfully.', 'success')
        return redirect(url_for('admin.manage_users'))
    return render_template(
        'admin/user_form.html',
        title='Create User',
        form=form,
        action='create'
    )


@admin_bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    """Edit an existing user"""
    user = User.query.get_or_404(user_id)
    form = AdminEditUserForm(
        original_username=user.username,
        original_email=user.email,
        obj=user
    )
    if form.validate_on_submit():
        # Prevent admin from removing their own admin privileges
        if user.id == current_user.id and not form.is_admin.data:
            flash('You cannot remove your own admin privileges.', 'danger')
            return redirect(url_for('admin.edit_user', user_id=user_id))
        user.username = form.username.data
        user.email = form.email.data
        user.is_admin = form.is_admin.data
        if form.password.data:
            user.set_password(form.password.data)
        db.session.commit()
        flash(f'User "{user.username}" has been updated successfully.', 'success')
        return redirect(url_for('admin.manage_users'))
    return render_template(
        'admin/user_form.html',
        title='Edit User',
        form=form,
        action='edit',
        user=user
    )


@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    """Delete a user"""
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('You cannot delete your own account.', 'danger')
        return redirect(url_for('admin.manage_users'))
    username = user.username
    db.session.delete(user)
    db.session.commit()
    flash(f'User "{username}" has been deleted.', 'warning')
    return redirect(url_for('admin.manage_users'))
