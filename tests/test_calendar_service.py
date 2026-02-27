import pytest
from types import SimpleNamespace
from datetime import datetime, timedelta

from app.services.calendar_service import CalendarService
from app.exceptions import ValidationError, NotFoundError, AuthorizationError
from app.models import Task


def make_creds():
    return SimpleNamespace(
        token='t',
        refresh_token='r',
        token_uri='u',
        client_id='cid',
        client_secret='cs',
        scopes=['scope']
    )


def test_connect_google_calendar_counts_unsynced(db_session, test_user):
    # create two unsynced tasks with due_dates
    t1 = Task(title='A', user_id=test_user.id, due_date=datetime.now())
    t2 = Task(title='B', user_id=test_user.id, due_date=datetime.now())
    db_session.session.add_all([t1, t2])
    db_session.session.commit()

    creds = make_creds()
    count = CalendarService.connect_google_calendar(test_user, creds)
    assert isinstance(count, int) and count >= 2
    assert test_user.calendar_sync_enabled is True
    assert test_user.google_token is not None


def test_disconnect_google_calendar_and_not_found(db_session, test_user):
    # successful disconnect
    test_user.google_token = '{}'
    test_user.calendar_sync_enabled = True
    db_session.session.commit()
    CalendarService.disconnect_google_calendar(test_user.id)
    db_session.session.refresh(test_user)
    assert test_user.google_token is None
    assert test_user.calendar_sync_enabled is False

    # missing user
    with pytest.raises(NotFoundError):
        CalendarService.disconnect_google_calendar(99999)


def test_calculate_date_range_views():
    t = datetime(2024, 2, 14, 12, 0, 0)
    s, e = CalendarService.calculate_date_range(t, 'day')
    assert s.hour == 0 and e.hour == 23

    s, e = CalendarService.calculate_date_range(t, 'month')
    assert s.day == 1

    s, e = CalendarService.calculate_date_range(t, 'upcoming')
    assert (e - s).days >= 7


def test_get_calendar_events_filters_and_connected(monkeypatch, db_session, test_user):
    # Create a synced task and an unsynced one
    now = datetime.now()
    t_synced = Task(title='S', user_id=test_user.id, due_date=now, google_event_id='e1', synced_to_calendar=True)
    t_unsynced = Task(title='U', user_id=test_user.id, due_date=now)
    db_session.session.add_all([t_synced, t_unsynced])
    db_session.session.commit()

    # simulate connected and calendar returns event with id 'e1' and another 'e2'
    monkeypatch.setattr('app.services.calendar_service.get_calendar_service', lambda user: True)
    monkeypatch.setattr('app.services.calendar_service.get_events_for_date_range', lambda svc, s, e: [{'id': 'e1'}, {'id': 'e2'}])

    test_user.calendar_sync_enabled = True
    test_user.google_token = '{}'
    db_session.session.commit()

    res = CalendarService.get_calendar_events(test_user, now - timedelta(days=1), now + timedelta(days=1), view='week')
    assert res['calendar_connected'] is True
    # e1 should be filtered out because it's linked to task
    assert any(ev.get('id') == 'e2' for ev in res['calendar_events'])
    assert any(t['title'] == 'S' for t in res['tasks'])


def test_create_event_success_and_failure(monkeypatch, db_session, test_user):
    # No connection
    test_user.calendar_sync_enabled = False
    db_session.session.commit()
    with pytest.raises(ValidationError):
        CalendarService.create_event(test_user, {'title': 'x'})

    # Connected but service fails
    test_user.calendar_sync_enabled = True
    test_user.google_token = '{}'
    db_session.session.commit()

    class FakeEvents:
        def __init__(self, ok=True):
            self._ok = ok
        def insert(self, calendarId=None, body=None):
            ok = self._ok
            class Exec:
                def execute(self):
                    if not ok:
                        raise Exception('fail')
                    return {'id': 'evt1'}
            return Exec()

    class FakeService:
        def events(self):
            return FakeEvents()

    monkeypatch.setattr('app.services.calendar_service.get_calendar_service', lambda user: FakeService())
    # success
    eid = CalendarService.create_event(test_user, {'title': 't', 'start': 's', 'end': 'e'})
    assert eid == 'evt1'

    # simulate insert error
    def bad_insert(user):
        class Bad:
            def events(self):
                class E:
                    def insert(self, calendarId=None, body=None):
                        class Exec:
                            def execute(self):
                                raise Exception('boom')
                        return Exec()
                return E()
        return Bad()

    monkeypatch.setattr('app.services.calendar_service.get_calendar_service', bad_insert)
    with pytest.raises(ValidationError):
        CalendarService.create_event(test_user, {'title': 't', 'start': 's', 'end': 'e'})


def test_sync_task_create_update_and_errors(monkeypatch, db_session, test_user, test_user_2):
    # create a task without google_event_id
    t = Task(title='X', user_id=test_user.id, due_date=datetime.now())
    db_session.session.add(t)
    db_session.session.commit()

    # ensure user is connected
    test_user.calendar_sync_enabled = True
    test_user.google_token = '{}'
    db_session.session.commit()

    # create path
    monkeypatch.setattr('app.services.calendar_service.get_calendar_service', lambda u: True)
    monkeypatch.setattr('app.services.calendar_service.create_calendar_event', lambda svc, task: 'evtid')
    msg = CalendarService.sync_task(t.id, test_user.id)
    assert 'synced' in msg.lower()
    db_session.session.refresh(t)
    assert t.google_event_id is not None

    # update path
    t2 = Task(title='Y', user_id=test_user.id, due_date=datetime.now(), google_event_id='abc')
    db_session.session.add(t2)
    db_session.session.commit()
    monkeypatch.setattr('app.services.calendar_service.update_calendar_event', lambda svc, eid, task: True)
    msg2 = CalendarService.sync_task(t2.id, test_user.id)
    assert 'updated' in msg2.lower()

    # not found
    with pytest.raises(NotFoundError):
        CalendarService.sync_task(9999, test_user.id)

    # authorization
    t3 = Task(title='Z', user_id=test_user_2.id, due_date=datetime.now())
    db_session.session.add(t3)
    db_session.session.commit()
    with pytest.raises(AuthorizationError):
        CalendarService.sync_task(t3.id, test_user.id)

    # user not connected
    test_user.calendar_sync_enabled = False
    db_session.session.commit()
    with pytest.raises(ValidationError):
        CalendarService.sync_task(t.id, test_user.id)


def test_remove_task_from_calendar_success_and_errors(monkeypatch, db_session, test_user):
    # create task with google_event_id
    t = Task(title='R', user_id=test_user.id, due_date=datetime.now(), google_event_id='ev1', synced_to_calendar=True)
    db_session.session.add(t)
    db_session.session.commit()

    test_user.calendar_sync_enabled = True
    test_user.google_token = '{}'
    db_session.session.commit()

    monkeypatch.setattr('app.services.calendar_service.get_calendar_service', lambda u: True)
    monkeypatch.setattr('app.services.calendar_service.delete_calendar_event', lambda svc, eid: True)
    CalendarService.remove_task_from_calendar(t.id, test_user.id)
    db_session.session.refresh(t)
    assert t.google_event_id is None

    # not found
    with pytest.raises(NotFoundError):
        CalendarService.remove_task_from_calendar(9999, test_user.id)

    # unauthorized
    t2 = Task(title='Q', user_id=99999, due_date=datetime.now(), google_event_id='x')
    db_session.session.add(t2)
    db_session.session.commit()
    with pytest.raises(AuthorizationError):
        CalendarService.remove_task_from_calendar(t2.id, test_user.id)

    # not synced
    t3 = Task(title='U', user_id=test_user.id, due_date=datetime.now())
    db_session.session.add(t3)
    db_session.session.commit()
    with pytest.raises(ValidationError):
        CalendarService.remove_task_from_calendar(t3.id, test_user.id)


def test_update_and_delete_event(monkeypatch, test_user):
    # update: service missing
    monkeypatch.setattr('app.services.calendar_service.get_calendar_service', lambda u: None)
    with pytest.raises(ValidationError):
        CalendarService.update_event(test_user, 'e1', {'summary': 'x'})

    # delete: service missing
    monkeypatch.setattr('app.services.calendar_service.get_calendar_service', lambda u: None)
    with pytest.raises(ValidationError):
        CalendarService.delete_event(test_user, 'e1')
