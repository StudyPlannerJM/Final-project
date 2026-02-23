# User Management & Admin Feature — Implementation Notes

## Overview

This document describes every change made to add **multi-user support** and an **admin "Manage Users" panel** to the Study Planner application.

The existing admin login (`admin@admin.com / admin`) and all current functionality were preserved. Three test student accounts were created for development/testing purposes.

---

## Files Modified

### 1. `app/models.py`
**Change:** Added `is_admin` boolean column to the `User` model.

```python
is_admin = db.Column(db.Boolean, default=False, nullable=False)
```

- Defaults to `False` for all regular users.
- Set to `True` only for administrator accounts.
- Controls visibility of the "Manage Users" sidebar link and access to all `/admin/*` routes.

---

### 2. `app/decorators.py`
**Change:** Added a new `admin_required` decorator.

```python
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403, description='Administrator access required.')
        return f(*args, **kwargs)
    return decorated_function
```

- Must be stacked **after** `@login_required`.
- Returns HTTP 403 Forbidden if the logged-in user does not have `is_admin=True`.

---

### 3. `app/forms.py`
**Change:** Added two new WTForms classes at the bottom of the file.

#### `AdminCreateUserForm`
Used by the admin to create a brand-new user.

| Field | Type | Notes |
|---|---|---|
| `username` | StringField | Required, validated unique |
| `email` | StringField | Required, validated unique |
| `password` | PasswordField | Required |
| `password2` | PasswordField | Must match `password` |
| `is_admin` | BooleanField | Grant admin privileges |

#### `AdminEditUserForm`
Used by the admin to modify an existing user.

| Field | Type | Notes |
|---|---|---|
| `username` | StringField | Required, unique (excluding current) |
| `email` | StringField | Required, unique (excluding current) |
| `password` | PasswordField | Optional — leave blank to keep current password |
| `password2` | PasswordField | Must match `password` if provided |
| `is_admin` | BooleanField | Toggle admin privileges |

Both forms accept the original `username` and `email` in their `__init__` so uniqueness validation correctly ignores the user's own existing values.

---

### 4. `app/routes/admin.py` *(new file)*
**Change:** Created a new Flask Blueprint `admin_bp` registered at `/admin`.

| Route | Method(s) | Function | Description |
|---|---|---|---|
| `/admin/users` | GET | `manage_users` | List all users in a table |
| `/admin/users/new` | GET, POST | `create_user` | Form to create a new user |
| `/admin/users/<id>/edit` | GET, POST | `edit_user` | Form to edit an existing user |
| `/admin/users/<id>/delete` | POST | `delete_user` | Delete a user (self-delete blocked) |

All routes are protected with `@login_required` and `@admin_required`.

---

### 5. `app/routes/__init__.py`
**Change:** Imported and exported the new `admin_bp`.

```python
from .admin import admin_bp

__all__ = [..., 'admin_bp']
```

---

### 6. `app/__init__.py`
**Change:** Registered `admin_bp` in the Flask application factory.

```python
from app.routes import (..., admin_bp)
app.register_blueprint(admin_bp)  # /admin
```

---

### 7. `app/templates/base.html`
**Change:** Added a "Manage Users" link in the sidebar, visible **only** to admin users.

```html
{% if current_user.is_authenticated and current_user.is_admin %}
<li class="nav-item">
    <a href="{{ url_for('admin.manage_users') }}" class="nav-link">
        <i class="fas fa-users-cog"></i><span>Manage Users</span>
    </a>
</li>
{% endif %}
```

Regular (non-admin) users see no difference in the sidebar.

---

### 8. `run.py`
**Change:** Updated the startup seed block to:

1. **Ensure the existing admin account has `is_admin=True`** (retroactively fixes old records).
2. **Create three test student accounts** if they don't already exist.

```python
# Promote existing admin
if not admin.is_admin:
    admin.is_admin = True
    db.session.commit()

# Create test students
test_users = [
    {"username": "student1", "email": "student1@study.com"},
    {"username": "student2", "email": "student2@study.com"},
    {"username": "student3", "email": "student3@study.com"},
]
for u_data in test_users:
    student = User(username=..., email=..., is_admin=False)
    student.set_password("user123")
    db.session.add(student)
db.session.commit()
```

---

## Files Created

### `app/templates/admin/manage_users.html`
The admin **Manage Users** list page. Features:

- Table displaying all users with ID, username, email, and role badge (Admin / User).
- **Edit** button linking to the edit form.
- **Delete** button (with confirmation dialog) submitting a POST form — hidden for the currently logged-in admin to prevent self-deletion.
- Empty state illustration if no users exist.
- "Add New User" button in the page header.

### `app/templates/admin/user_form.html`
Shared form template used for both **Create** and **Edit** operations. Features:

- Renders all form fields with inline validation error messages.
- "Save" and "Cancel" (back to list) buttons.
- Styled consistently with the existing application UI using CSS variables.

---

## Database Migration

A new Alembic migration was generated and applied:

**File:** `migrations/versions/ef30f8981f68_add_is_admin_to_user.py`

The migration adds the `is_admin` column using `server_default=sa.false()` to satisfy SQLite's constraint that a NOT NULL column must have a server-side default when added to an existing table.

```python
batch_op.add_column(
    sa.Column('is_admin', sa.Boolean(), nullable=False, server_default=sa.false())
)
```

Applied with:
```bash
flask db upgrade
```

---

## Test Accounts

| Username | Email | Password | Role |
|---|---|---|---|
| admin | admin@admin.com | admin | **Admin** |
| student1 | student1@study.com | user123 | User |
| student2 | student2@study.com | user123 | User |
| student3 | student3@study.com | user123 | User |

---

## Access Control Summary

| Who | Can access `/admin/*` | Sees "Manage Users" in sidebar |
|---|---|---|
| Unauthenticated | No (redirected to login) | No |
| Regular user (`is_admin=False`) | No (403 Forbidden) | No |
| Admin (`is_admin=True`) | Yes | Yes |

---

## How to Use

1. Start the app: `python run.py`
2. Log in as `admin@admin.com` / `admin`
3. Click **Manage Users** in the left sidebar
4. From there you can:
   - **Add** a new user via the "Add New User" button
   - **Edit** any user's username, email, password, or admin status
   - **Delete** any user except yourself
