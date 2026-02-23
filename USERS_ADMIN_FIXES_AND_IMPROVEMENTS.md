# User Management — Bug Fixes & Improvements Log

This document covers all changes made after the initial implementation described in `USERS_ADMIN_FEATURE.md`.

---

## Issue 1 — Internal Server Error on `/admin/users`

### Symptom
Clicking "Manage Users" as admin returned a generic **500 Internal Server Error** page.

### Root Cause
The delete forms inside `manage_users.html` contained these two lines:

```html
{{ csrf_token_field() if csrf_token_field is defined }}
<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
```

`csrf_token()` is a helper provided by Flask-WTF's `CSRFProtect` extension. This project does **not** initialize `CSRFProtect` globally — it relies on `form.hidden_tag()` inside WTForms objects instead. Calling `csrf_token()` as a plain Jinja2 function therefore raised an `UndefinedError` and crashed the page.

### Fix — `app/templates/admin/manage_users.html`
Removed both CSRF lines from the raw HTML delete form, leaving only the submit button:

```html
<form action="{{ url_for('admin.delete_user', user_id=user.id) }}" method="post"
      onsubmit="return confirm('Delete user ...?');">
    <button type="submit" class="btn-icon btn-delete">
        <i class="fas fa-trash-alt"></i> Delete
    </button>
</form>
```

---

## Issue 2 — Old Server Process Serving Stale Code

### Symptom
Even after applying the fix above, the 500 error persisted.

### Root Cause
The PowerShell Extension terminal had its own Python/Flask process still listening on port 5000, running the **unfixed** version of the code. The newly started server was not the one receiving browser requests.

### Fix
Killed **all** Python processes and started a clean server:

```powershell
Get-Process -Name python,python3 | Stop-Process -Force
python run.py
```

Also switched `app.run(debug=False)` → `app.run(debug=True)` in `run.py` so future errors show a detailed traceback in the browser instead of a generic 500 page.

---

## UI Improvement 1 — Sidebar Order

### Change — `app/templates/base.html`
Moved the **Manage Users** sidebar link to appear **above Settings** instead of below it, giving admin actions higher priority in the navigation hierarchy.

```
Before:   Settings → Manage Users
After:    Manage Users → Settings
```

---

## UI Improvement 2 — Black Text in Manage Users Table

### Change — `app/templates/admin/manage_users.html`
Added `color: #000` to `.users-table td` so username, email, and other cell text renders in black regardless of the active theme (light or dark).

---

## UI Improvement 3 — Black Text in Edit User Form

### Symptom
In dark mode, the Username and Email fields showed white/grey text on a dark background, making them unreadable (as shown in the attached screenshot).

### Root Cause
The inputs inherited `color` and `background` from the dark theme's CSS variables. The browser's autofill behaviour also applied its own dark overlay independently.

### Fix — `app/templates/admin/user_form.html`
Four targeted changes:

| Element | Fix applied |
|---|---|
| `.form-card` | Hardcoded `background: #fff` and `color: #000` — removes theme variable |
| `.form-group label` | Added `color: #000` |
| Input fields | `background: #fff !important` and `color: #000 !important` |
| Browser autofill | Added `-webkit-box-shadow: 0 0 0px 1000px #fff inset` to neutralise dark autofill overlay |
| `.form-check` | Added `color: #000` for the "Admin Privileges" checkbox label |

---

## Review & Remaining Improvements

A full code review of all added files identified five further issues, all fixed in one pass:

### Fix 1 — Table Header Text Was Black (Invisible on Purple)

**File:** `app/templates/admin/manage_users.html`

The shared `th, td { color: #000 }` rule was overriding the `thead tr { color: #fff }` rule, making header text black on top of the purple header row — effectively invisible.

**Fix:** Split into separate rules:
- `th { color: #fff }` — white text for the purple header
- `td { color: #000 }` — black text for data rows

---

### Fix 2 — No Password Minimum Length Validation

**File:** `app/forms.py`

Both `AdminCreateUserForm` and `AdminEditUserForm` accepted passwords of any length, including single characters.

**Fix:** Added `Length` validators:

```python
# Create form
password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])

# Edit form
password = PasswordField('...', validators=[Optional(), Length(min=6)])

# Both forms
username = StringField('Username', validators=[DataRequired(), Length(min=3, max=64)])
email    = StringField('Email',    validators=[DataRequired(), Email(), Length(max=120)])
```

---

### Fix 3 — Admin Could Remove Their Own Admin Privileges

**File:** `app/routes/admin.py`

An admin editing their own account could uncheck "Admin Privileges" and save, silently locking themselves out of the admin panel with no way to recover.

**Fix:** Added a guard in `edit_user()`:

```python
if user.id == current_user.id and not form.is_admin.data:
    flash('You cannot remove your own admin privileges.', 'danger')
    return redirect(url_for('admin.edit_user', user_id=user_id))
```

---

### Fix 4 — Edit Form Title Showed No Context

**File:** `app/templates/admin/user_form.html`

The page title always read "Edit User" with no indication of which user was being edited.

**Fix:** The page title now includes the username when in edit mode:

```html
{% block page_title %}
    {{ title }}{% if action == 'edit' and user %} — {{ user.username }}{% endif %}
{% endblock %}
```

Example: **Edit User — student1**

---

### Fix 5 — Form Card Was Left-Aligned on Wide Screens

**File:** `app/templates/admin/user_form.html`

The form card used a `max-width: 560px` but had no horizontal centering, so it was pinned to the left side of the page on wide monitors.

**Fix:** Added `margin: 0 auto` inline:

```html
<div class="form-card" style="margin: 0 auto;">
```

---

## Summary of All Files Changed in This Session

| File | Changes |
|---|---|
| `app/templates/admin/manage_users.html` | Removed `csrf_token()` call; fixed `th` vs `td` color split |
| `app/templates/admin/user_form.html` | Fixed dark mode colors; centered card; added username to page title |
| `app/routes/admin.py` | Blocked admin self-demotion |
| `app/forms.py` | Added `Length` validators; imported `Length` from `wtforms.validators` |
| `run.py` | Enabled `debug=True` |
