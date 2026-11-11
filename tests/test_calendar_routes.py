from types import SimpleNamespace
from app.exceptions import ValidationError, NotFoundError, AuthorizationError

def test_authorize_redirects(monkeypatch, auth_client):
    class FakeFlow:
        def authorization_url(self, **kw):
            return ('https://accounts.example/auth', 'STATE123')

    monkeypatch.setattr('app.routes.calendar_routes.get_google_auth_flow', lambda: FakeFlow())

    resp = auth_client.get('/calendar/authorize')
    assert resp.status_code == 302
    assert resp.headers['Location'] == 'https://accounts.example/auth'


def test_oauth2callback_redirects_based_on_unsynced(monkeypatch, auth_client, test_user):
    class FakeFlow:
        def authorization_url(self, **kw):
            return ('https://a', 'S')
        def fetch_token(self, authorization_response=None):
            pass
        @property
        def credentials(self):
            return SimpleNamespace(token='tok')

    monkeypatch.setattr('app.routes.calendar_routes.get_google_auth_flow', lambda: FakeFlow())
    # unsynced >0 -> redirect to sync_prompt
    monkeypatch.setattr('app.routes.calendar_routes.CalendarService.connect_google_calendar', lambda user, creds: 2)
    # A real callback carries the state stored when the flow started
    with auth_client.session_transaction() as sess:
        sess['state'] = 'S'
    resp = auth_client.get('/calendar/oauth2callback?state=S')
    assert resp.status_code == 302
    assert '/calendar/sync_prompt' in resp.headers['Location']

    # unsynced == 0 -> redirect to schedule
    monkeypatch.setattr('app.routes.calendar_routes.CalendarService.connect_google_calendar', lambda user, creds: 0)
    with auth_client.session_transaction() as sess:
        sess['state'] = 'S'
    resp = auth_client.get('/calendar/oauth2callback?state=S')
    assert resp.status_code == 302
    assert resp.headers['Location'].endswith('/calendar/schedule')


def test_schedule_shows_calendar_connected_flag(auth_client, db_session, test_user):
    # default: calendar not connected
    resp = auth_client.get('/calendar/schedule')
    assert resp.status_code == 200

    # mark connected
    test_user.calendar_sync_enabled = True
    test_user.google_token = 'token'
    db_session.session.commit()

    resp = auth_client.get('/calendar/schedule')
    assert resp.status_code == 200
    assert b'Schedule' in resp.data


def test_api_events_returns_json(monkeypatch, auth_client):
    # stub date range calculation
    monkeypatch.setattr('app.routes.calendar_routes.CalendarService.calculate_date_range', lambda t, v: (t, t))
    monkeypatch.setattr('app.routes.calendar_routes.CalendarService.get_calendar_events', lambda user, s, e, v: {
        'calendar_connected': True,
        'calendar_events': [{'id':'e1'}],
        'tasks': [{'id': 't1'}],
        'week_dates': ['2024-01-01']
    })

    resp = auth_client.get('/calendar/api/events?date=2024-01-01&view=week')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['success'] is True
    assert data['calendarConnected'] is True
    assert 'calendarEvents' in data and 'tasks' in data


def test_api_create_event_success_and_validation(monkeypatch, auth_client):
    monkeypatch.setattr('app.routes.calendar_routes.CalendarService.create_event', lambda user, data: 'evt123')
    resp = auth_client.post('/calendar/api/create_event', json={'title': 'X'})
    assert resp.status_code == 200
    j = resp.get_json()
    assert j['success'] is True and j['event_id'] == 'evt123'

    def raise_val(user, data):
        raise ValidationError('bad')

    monkeypatch.setattr('app.routes.calendar_routes.CalendarService.create_event', raise_val)
    resp = auth_client.post('/calendar/api/create_event', json={'title': 'X'})
    assert resp.status_code == 400


def test_sync_task_and_error_cases(monkeypatch, auth_client):
    # success
    monkeypatch.setattr('app.routes.calendar_routes.CalendarService.sync_task', lambda task_id, uid: 'synced')
    resp = auth_client.post('/calendar/sync_task/1')
    assert resp.status_code == 200
    assert resp.get_json()['success'] is True

    # NotFound
    def nf(tid, uid):
        raise NotFoundError('no')

    monkeypatch.setattr('app.routes.calendar_routes.CalendarService.sync_task', nf)
    resp = auth_client.post('/calendar/sync_task/999')
    assert resp.status_code == 404

    # Authorization
    def autherr(tid, uid):
        raise AuthorizationError('denied')

    monkeypatch.setattr('app.routes.calendar_routes.CalendarService.sync_task', autherr)
    resp = auth_client.post('/calendar/sync_task/1')
    assert resp.status_code == 403

    # Validation
    def valerr(tid, uid):
        raise ValidationError('bad')

    monkeypatch.setattr('app.routes.calendar_routes.CalendarService.sync_task', valerr)
    resp = auth_client.post('/calendar/sync_task/1')
    assert resp.status_code == 400


def test_remove_task_and_update_delete(monkeypatch, auth_client):
    monkeypatch.setattr('app.routes.calendar_routes.CalendarService.remove_task_from_calendar', lambda tid, uid: None)
    resp = auth_client.post('/calendar/remove_task/1')
    assert resp.status_code == 200

    monkeypatch.setattr('app.routes.calendar_routes.CalendarService.update_event', lambda user, eid, data: None)
    resp = auth_client.post('/calendar/update_event/evt1', json={'a':1})
    assert resp.status_code == 200

    monkeypatch.setattr('app.routes.calendar_routes.CalendarService.delete_event', lambda user, eid: None)
    resp = auth_client.post('/calendar/delete_event/evt1')
    assert resp.status_code == 200
