"""Phase 4: CSRF protection, sign-in limits, error pages and security headers."""

import re
from contextlib import contextmanager
from pathlib import Path


from app.models import Task

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = ROOT / 'app/templates'
STATIC_JS = ROOT / 'app/static/js'


@contextmanager
def csrf_enabled(app):
    previous = app.config.get('WTF_CSRF_ENABLED')
    app.config['WTF_CSRF_ENABLED'] = True
    try:
        yield
    finally:
        app.config['WTF_CSRF_ENABLED'] = previous


def _token(client, url='/'):
    html = client.get(url).get_data(as_text=True)
    return re.search(r'<meta name="csrf-token" content="([^"]+)"', html).group(1)


def _task(db_session, user, title='Task'):
    task = Task(title=title, user_id=user.id, status='todo')
    db_session.session.add(task)
    db_session.session.commit()
    return task.id


# --- CSRF ------------------------------------------------------------------

def test_every_post_form_in_the_templates_carries_a_token():
    missing = []
    for path in sorted(TEMPLATES.rglob('*.html')):
        html = path.read_text()
        for match in re.finditer(r'<form\b[^>]*>', html, re.I):
            if not re.search(r'method=["\']post["\']', match.group(0), re.I):
                continue
            body = html[match.end():html.find('</form>', match.end())]
            if 'csrf_token' not in body and 'hidden_tag' not in body:
                line = html.count('\n', 0, match.start()) + 1
                missing.append(f'{path.relative_to(TEMPLATES)}:{line}')
    assert missing == []


def test_app_pages_expose_the_token_for_scripts(auth_client):
    assert _token(auth_client)


def test_form_post_without_token_is_refused_with_a_friendly_page(app, auth_client, db_session, test_user):
    task_id = _task(db_session, test_user)
    with csrf_enabled(app):
        response = auth_client.post(f'/tasks/delete/{task_id}')
        assert response.status_code == 400
        assert 'session expired' in response.get_data(as_text=True).lower()
        assert db_session.session.get(Task, task_id) is not None

        token = _token(auth_client)
        ok = auth_client.post(f'/tasks/delete/{task_id}', data={'csrf_token': token})
        assert ok.status_code == 302
        db_session.session.expire_all()
        assert db_session.session.get(Task, task_id) is None


def test_json_post_without_token_gets_a_json_error(app, auth_client, db_session, test_user):
    task_id = _task(db_session, test_user)
    with csrf_enabled(app):
        response = auth_client.post(f'/tasks/update_status/{task_id}/doing', json={},
                                    headers={'Accept': 'application/json'})
        assert response.status_code == 400
        assert response.is_json and response.get_json()['success'] is False

        token = _token(auth_client)
        ok = auth_client.post(f'/tasks/update_status/{task_id}/doing', json={},
                              headers={'Accept': 'application/json', 'X-CSRFToken': token})
        assert ok.status_code == 200 and ok.get_json()['success'] is True


def test_scripts_send_the_token():
    common = (STATIC_JS / 'common.js').read_text()
    assert "headers.set('X-CSRFToken'" in common and 'window.fetch = ' in common
    for name in ('tasks.js', 'edit-task.js'):
        assert 'csrf_token' in (STATIC_JS / name).read_text(), name


def test_logout_needs_a_post(auth_client):
    auth_client.get('/auth/logout')
    assert auth_client.get('/').status_code == 200          # still signed in
    response = auth_client.post('/auth/logout', follow_redirects=True)
    assert 'logged out' in response.get_data(as_text=True)
    assert auth_client.get('/').status_code == 302          # signed out


def test_calendar_disconnect_needs_a_post(auth_client, monkeypatch):
    calls = []
    from app.services.calendar_service import CalendarService
    monkeypatch.setattr(CalendarService, 'disconnect_google_calendar',
                        staticmethod(lambda user_id: calls.append(user_id)))
    auth_client.get('/calendar/disconnect')
    assert calls == []
    auth_client.post('/calendar/disconnect')
    assert len(calls) == 1
