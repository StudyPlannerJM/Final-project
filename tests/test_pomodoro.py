import json
import datetime
from types import SimpleNamespace
from app.models import PomodoroSession
from app.exceptions import ValidationError, NotFoundError


def make_session(user_id, duration=25, completed=True, created_at=None, notes=None):
    if created_at is None:
        created_at = datetime.datetime.now()
    # PomodoroSession requires user_id and start_time in its constructor
    return PomodoroSession(
        user_id,
        start_time=created_at,
        duration_minutes=duration,
        completed=completed,
        notes=notes,
        created_at=created_at
    )


def test_index_shows_last_three_sessions(db_session, auth_client, test_user):
    # create 4 sessions; only latest 3 should be rendered
    times = [datetime.datetime(2021, 1, i+1) for i in range(4)]
    sessions = [make_session(test_user.id, duration=10 + i, completed=(i % 2 == 0), created_at=times[i]) for i in range(4)]

    for s in sessions:
        db_session.session.add(s)
    db_session.session.commit()

    resp = auth_client.get('/pomodoro/')
    assert resp.status_code == 200
    data = resp.data
    # latest three durations (for days 2,3,4 -> durations 11,12,13)
    assert b'11 min' in data
    assert b'12 min' in data
    assert b'13 min' in data
    # oldest (10) should not be present
    assert b'10 min' not in data


def test_sessions_page_shows_stats_and_sessions(db_session, auth_client, test_user, monkeypatch):
    # create 2 sessions
    s1 = make_session(test_user.id, duration=25, completed=True)
    s2 = make_session(test_user.id, duration=15, completed=False, notes='Note')
    db_session.session.add_all([s1, s2])
    db_session.session.commit()

    # patch statistics
    monkeypatch.setattr('app.routes.pomodoro.PomodoroService.get_user_statistics', lambda uid: {
        'total_sessions': 2,
        'completed_sessions': 1,
        'total_minutes': 40
    })

    resp = auth_client.get('/pomodoro/sessions')
    assert resp.status_code == 200
    assert b'2' in resp.data  # total_sessions shown
    assert b'1' in resp.data  # completed_sessions shown
    assert b'40' in resp.data  # total_minutes shown
    assert b'Note' in resp.data


def test_delete_session_api_success(db_session, auth_client, test_user, monkeypatch):
    s = make_session(test_user.id, duration=30)
    db_session.session.add(s)
    db_session.session.commit()

    called = {'ok': False}

    def fake_delete(session_id, user_id):
        called['ok'] = True

    monkeypatch.setattr('app.routes.pomodoro.PomodoroService.delete_session', fake_delete)

    resp = auth_client.delete(f'/pomodoro/api/delete/{s.id}')
    assert resp.status_code == 200
    payload = resp.get_json()
    assert payload['success'] is True
    assert called['ok'] is True


def test_delete_session_api_not_found(monkeypatch, auth_client, db_session, test_user):
    # create a session for the user
    s = make_session(test_user.id)
    db_session.session.add(s)
    db_session.session.commit()

    def raise_nf(session_id, user_id):
        raise NotFoundError('Missing')

    monkeypatch.setattr('app.routes.pomodoro.PomodoroService.delete_session', raise_nf)

    resp = auth_client.delete(f'/pomodoro/api/delete/{s.id}')
    assert resp.status_code == 403
    payload = resp.get_json()
    assert payload['success'] is False
    assert b'Missing' in resp.data


def test_api_complete_success(monkeypatch, auth_client, test_user):
    fake_pom = SimpleNamespace(id=123)
    monkeypatch.setattr('app.routes.pomodoro.PomodoroService.create_session', lambda user_id, duration, task_id, completed: (fake_pom, 90))

    resp = auth_client.post('/pomodoro/api/complete', data=json.dumps({'duration': 25}), content_type='application/json')
    assert resp.status_code == 200
    payload = resp.get_json()
    assert payload['success'] is True
    assert payload['session_id'] == 123
    assert payload['total_minutes_today'] == 90


def test_api_complete_no_data(auth_client):
    resp = auth_client.post('/pomodoro/api/complete', data=json.dumps({}), content_type='application/json')
    assert resp.status_code == 400
    payload = resp.get_json()
    assert payload['success'] is False
    assert b'No data provided' in resp.data


def test_api_complete_validation_error(monkeypatch, auth_client):
    def raise_val(*a, **k):
        raise ValidationError('Bad')

    monkeypatch.setattr('app.routes.pomodoro.PomodoroService.create_session', raise_val)

    resp = auth_client.post('/pomodoro/api/complete', data=json.dumps({'duration': 10}), content_type='application/json')
    assert resp.status_code == 400
    payload = resp.get_json()
    assert payload['success'] is False
    assert b'Bad' in resp.data
