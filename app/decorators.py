"""
Custom decorators for Flask routes
"""
from functools import wraps
from flask import abort
from flask_login import current_user


def admin_required(f):
    """
    Decorator to restrict a route to admin users only.
    Must be used after @login_required.

    Usage:
        @login_required
        @admin_required
        def admin_only_view():
            ...
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403, description='Administrator access required.')
        return f(*args, **kwargs)
    return decorated_function


def require_resource_ownership(model_class, id_param='id', user_field='user_id'):
    """
    Decorator to check if current user owns the resource.
    
    Args:
        model_class: The SQLAlchemy model class (e.g., Task, Summary)
        id_param: The parameter name from route that contains the resource ID (default: 'id')
        user_field: The field name in the model that contains the user ID (default: 'user_id')
    
    Usage:
        @require_resource_ownership(Task, id_param='task_id')
        def edit_task(task_id):
            task = Task.query.get_or_404(task_id)
            # User ownership already verified
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Get the resource ID from route parameters
            resource_id = kwargs.get(id_param)
            
            if resource_id is None:
                abort(400, description=f'Missing required parameter: {id_param}')
            
            # Fetch the resource from database
            resource = model_class.query.get_or_404(resource_id)
            
            # Check ownership
            resource_user_id = getattr(resource, user_field, None)
            
            # Handle special case where user_field might be a relationship (e.g., 'author')
            if resource_user_id is None:
                author = getattr(resource, 'author', None)
                if author:
                    resource_user_id = author.id
            
            # Verify ownership
            if resource_user_id != current_user.id:
                abort(403, description='You do not have permission to access this resource')
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator
