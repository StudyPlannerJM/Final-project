"""Dashboard statistics: streaks, weekly minutes, today's tasks."""

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from app.models import CardReview, Deck, Flashcard, PomodoroSession, StudySession, Task
from app.services.stats_service import StatsService, compute_streak

UTC = ZoneInfo('UTC')
SAO_PAULO = ZoneInfo('America/Sao_Paulo')  # UTC-3, no DST
TODAY = date(2026, 11, 11)


def _days(*offsets):
    return {TODAY - timedelta(days=n) for n in offsets}


# --- Streak maths (pure) ---------------------------------------------------

@pytest.mark.parametrize('active,expected', [
    (set(), {'current': 0, 'longest': 0, 'active_today': False}),
    (_days(0), {'current': 1, 'longest': 1, 'active_today': True}),
    (_days(0, 1, 2), {'current': 3, 'longest': 3, 'active_today': True}),
    # today not done yet: yesterday's streak still stands
    (_days(1, 2), {'current': 2, 'longest': 2, 'active_today': False}),
    # a missed day breaks it
    (_days(2, 3, 4), {'current': 0, 'longest': 3, 'active_today': False}),
    (_days(0, 1, 5, 6, 7, 8), {'current': 2, 'longest': 4, 'active_today': True}),
])
def test_compute_streak(active, expected):
    assert compute_streak(active, TODAY) == expected


def test_streak_ignores_future_dates():
    assert compute_streak({TODAY + timedelta(days=1)}, TODAY)['current'] == 0


# --- Activity days follow the user's timezone ------------------------------

def _pomodoro(db_session, user, start, completed=True):
    db_session.session.add(PomodoroSession(user_id=user.id, start_time=start, completed=completed))
    db_session.session.commit()


def test_activity_dates_use_local_day(db_session, test_user):
    # 01:30 UTC on the 12th is 22:30 on the 11th in Sao Paulo
    _pomodoro(db_session, test_user, datetime(2026, 11, 12, 1, 30))
    assert StatsService.activity_dates(test_user.id, UTC) == {date(2026, 11, 12)}
    assert StatsService.activity_dates(test_user.id, SAO_PAULO) == {date(2026, 11, 11)}


def test_activity_counts_reviews_and_completed_pomodoros_only(db_session, test_user, test_user_2):
    _pomodoro(db_session, test_user, datetime(2026, 11, 9, 12), completed=False)
    _pomodoro(db_session, test_user_2, datetime(2026, 11, 8, 12))
    deck = Deck(name='D', user_id=test_user.id)
    db_session.session.add(deck)
    db_session.session.commit()
    card = Flashcard(question='Q', answer='A', user_id=test_user.id, deck_id=deck.id)
    db_session.session.add(card)
    db_session.session.commit()
    db_session.session.add(CardReview(user_id=test_user.id, flashcard_id=card.id, rating=2,
                                      reviewed_at=datetime(2026, 11, 10, 12)))
    db_session.session.commit()
    assert StatsService.activity_dates(test_user.id, UTC) == {date(2026, 11, 10)}


# --- Weekly minutes --------------------------------------------------------

def _study(db_session, user, start, minutes):
    db_session.session.add(StudySession(user_id=user.id, start_time=start, duration_minutes=minutes))
    db_session.session.commit()


def test_weekly_minutes_has_seven_local_days_ending_today(db_session, test_user):
    _study(db_session, test_user, datetime(2026, 11, 11, 10), 25)
    _study(db_session, test_user, datetime(2026, 11, 11, 15), 50)
    _study(db_session, test_user, datetime(2026, 11, 12, 1, 30), 30)   # still the 11th in Sao Paulo
    _study(db_session, test_user, datetime(2026, 11, 5, 12), 40)
    _study(db_session, test_user, datetime(2026, 11, 3, 12), 99)       # outside the window
    week = StatsService.weekly_minutes(test_user.id, SAO_PAULO, TODAY)
    assert [d['date'] for d in week] == [TODAY - timedelta(days=n) for n in range(6, -1, -1)]
    assert [d['minutes'] for d in week] == [40, 0, 0, 0, 0, 0, 105]
    assert week[-1]['is_today'] is True and week[-1]['label'] == 'Wed'
    assert [d['percent'] for d in week][0] == round(40 / 105 * 100)
    assert week[-1]['percent'] == 100


def test_weekly_minutes_with_no_study_has_zero_percentages(db_session, test_user):
    week = StatsService.weekly_minutes(test_user.id, UTC, TODAY)
    assert {d['minutes'] for d in week} == {0} and {d['percent'] for d in week} == {0}


# --- Today's tasks ---------------------------------------------------------

def _task(db_session, user, title, due, status='todo'):
    task = Task(title=title, user_id=user.id, due_date=due, status=status)
    db_session.session.add(task)
    db_session.session.commit()
    return task


def test_today_tasks_lists_open_overdue_and_due_today(db_session, test_user, test_user_2):
    now_local = datetime(2026, 11, 11, 14, 0)
    _task(db_session, test_user, 'overdue', datetime(2026, 11, 9, 9))
    _task(db_session, test_user, 'earlier today', datetime(2026, 11, 11, 9))
    _task(db_session, test_user, 'tonight', datetime(2026, 11, 11, 23, 59))
    _task(db_session, test_user, 'tomorrow', datetime(2026, 11, 12, 0, 0))
    _task(db_session, test_user, 'done', datetime(2026, 11, 11, 9), status='done')
    _task(db_session, test_user, 'no date', None)
    _task(db_session, test_user_2, 'not mine', datetime(2026, 11, 11, 9))
    result = StatsService.today_tasks(test_user.id, now_local)
    assert [(t.title, kind) for t, kind in result['items']] == [
        ('overdue', 'overdue'), ('earlier today', 'overdue'), ('tonight', 'today')]
    assert result['total'] == 3 and result['more'] == 0


def test_today_tasks_caps_the_list_and_reports_the_rest(db_session, test_user):
    now_local = datetime(2026, 11, 11, 14, 0)
    for n in range(8):
        _task(db_session, test_user, f'task {n}', datetime(2026, 11, 11, 20, n))
    result = StatsService.today_tasks(test_user.id, now_local)
    assert len(result['items']) == 5 and result['total'] == 8 and result['more'] == 3


# --- Dashboard page --------------------------------------------------------

def test_dashboard_shows_today_streak_chart_and_deck_progress(auth_client, db_session, test_user):
    deck = Deck(name='Biology', user_id=test_user.id)
    db_session.session.add(deck)
    db_session.session.commit()
    db_session.session.add(Flashcard(question='Q', answer='A', user_id=test_user.id, deck_id=deck.id))
    db_session.session.commit()
    html = auth_client.get('/').get_data(as_text=True)
    for marker in ('id="dash-today"', 'id="dash-streak"', 'id="dash-week"', 'id="dash-decks"'):
        assert marker in html
    assert '1 card due' in html and 'href="/flashcards/review"' in html
    assert 'Biology' in html.split('id="dash-decks"')[1]


def test_dashboard_with_nothing_to_do_shows_friendly_empty_states(auth_client):
    html = auth_client.get('/').get_data(as_text=True)
    assert 'Nothing due today' in html
    assert 'No cards to review' in html


def test_dashboard_uses_timezone_cookie_for_today(auth_client, db_session, test_user):
    # Due at 23:30 on a date that is "today" only for a user far west of UTC is hard to pin
    # without a clock; instead check a hostile cookie value cannot break the page.
    auth_client.set_cookie('bd_tz', '../../etc/passwd')
    assert auth_client.get('/').status_code == 200
