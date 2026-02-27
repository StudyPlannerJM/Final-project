import datetime
import pytest
from app.services.pomodoro_service import PomodoroService
from app.models import PomodoroSession, StudySession, Task
from app.exceptions import ValidationError, NotFoundError, AuthorizationError


def test_create_session_success(db_session, test_user):
    pom, total = PomodoroService.create_session(test_user.id, duration=25)

    assert isinstance(pom, PomodoroSession)
    assert pom.user_id == test_user.id
    assert pom.duration_minutes == 25
    # study session linked
    ss = db_session.session.get(StudySession, pom.study_session_id)
    assert ss is not None
    assert total >= 0


def test_create_session_user_not_found(db_session):
    with pytest.raises(NotFoundError):
        PomodoroService.create_session(999999, duration=25)


def test_create_session_invalid_duration(db_session, test_user):
    with pytest.raises(ValidationError):
        PomodoroService.create_session(test_user.id, duration=0)

    with pytest.raises(ValidationError):
        PomodoroService.create_session(test_user.id, duration=999)


def test_create_session_with_task_updates_task(db_session, test_user):
    # create a task for user
    t = Task(title='T', user_id=test_user.id)
    db_session.session.add(t)
    db_session.session.commit()

    pom, total = PomodoroService.create_session(test_user.id, duration=30, task_id=t.id)

    # reload task
    task = db_session.session.get(Task, t.id)
    assert task.actual_minutes == 30


def test_delete_session_success(db_session, test_user):
    # create a pomodoro session instance
    start = datetime.datetime.now()
    p = PomodoroSession(user_id=test_user.id, start_time=start, duration_minutes=20, completed=True)
    db_session.session.add(p)
    db_session.session.commit()

    PomodoroService.delete_session(p.id, test_user.id)
    assert db_session.session.get(PomodoroSession, p.id) is None


def test_delete_session_not_found(db_session, test_user):
    with pytest.raises(NotFoundError):
        PomodoroService.delete_session(99999, test_user.id)


def test_delete_session_authorization(db_session, test_user, test_user_2):
    start = datetime.datetime.now()
    p = PomodoroSession(user_id=test_user_2.id, start_time=start, duration_minutes=20, completed=True)
    db_session.session.add(p)
    db_session.session.commit()

    with pytest.raises(AuthorizationError):
        PomodoroService.delete_session(p.id, test_user.id)


def test_get_user_statistics_and_today_minutes(db_session, test_user):
    now = datetime.datetime.now()
    yesterday = now - datetime.timedelta(days=1)

    s1 = PomodoroSession(user_id=test_user.id, start_time=now, duration_minutes=25, completed=True)
    s2 = PomodoroSession(user_id=test_user.id, start_time=now, duration_minutes=15, completed=False)
    s3 = PomodoroSession(user_id=test_user.id, start_time=yesterday, duration_minutes=30, completed=True)
    db_session.session.add_all([s1, s2, s3])
    db_session.session.commit()

    stats = PomodoroService.get_user_statistics(test_user.id)
    assert stats['total_sessions'] == 3
    assert stats['completed_sessions'] == 2
    # total_minutes sums only completed sessions
    assert stats['total_minutes'] == 55

    # create study sessions for today and yesterday
    ss_today = StudySession(user_id=test_user.id, start_time=now, duration_minutes=40)
    ss_yesterday = StudySession(user_id=test_user.id, start_time=yesterday, duration_minutes=20)
    db_session.session.add_all([ss_today, ss_yesterday])
    db_session.session.commit()

    total_today = PomodoroService.get_today_study_minutes(test_user.id)
    assert total_today == 40
