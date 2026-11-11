"""
Dashboard statistics: study streak, weekly study minutes and today's tasks.

Database timestamps are UTC without tzinfo. Anything about a calendar day is
worked out in the user's timezone, which callers pass in.
"""

from datetime import datetime, time, timedelta

from app import db
from app.models import CardReview, PomodoroSession, StudySession, Task
from app.utils.timezone import day_bounds_utc, to_local

TODAY_TASK_LIMIT = 5
STREAK_WINDOW_DAYS = 365


def compute_streak(active_dates, today):
    """
    Work out streaks from the set of days with study activity.

    The current streak counts back from today, or from yesterday when today
    has no activity yet (the day is not over, so the streak is not broken).

    Returns:
        {'current': int, 'longest': int, 'active_today': bool}
    """
    days = sorted(day for day in active_dates if day <= today)
    longest = run = 0
    previous = None
    for day in days:
        run = run + 1 if previous is not None and day - previous == timedelta(days=1) else 1
        longest = max(longest, run)
        previous = day

    active = set(days)
    cursor = today if today in active else today - timedelta(days=1)
    current = 0
    while cursor in active:
        current += 1
        cursor -= timedelta(days=1)

    return {'current': current, 'longest': longest, 'active_today': today in active}


class StatsService:
    """Read-only queries behind the dashboard."""

    @staticmethod
    def activity_dates(user_id, tz, since=None):
        """
        Local calendar days on which the user completed a Pomodoro or reviewed a card.

        Args:
            since: optional local date; earlier activity is not read (keeps the
                dashboard query bounded for heavy users)
        """
        pomodoro_times = db.session.query(PomodoroSession.start_time).filter(
            PomodoroSession.user_id == user_id,
            PomodoroSession.completed.is_(True),
        )
        review_times = db.session.query(CardReview.reviewed_at).filter(CardReview.user_id == user_id)
        if since is not None:
            window_start, _ = day_bounds_utc(since, tz)
            pomodoro_times = pomodoro_times.filter(PomodoroSession.start_time >= window_start)
            review_times = review_times.filter(CardReview.reviewed_at >= window_start)
        return {
            to_local(stamp, tz).date()
            for (stamp,) in pomodoro_times.union_all(review_times).all()
            if stamp is not None
        }

    @staticmethod
    def streak(user_id, tz, today):
        """Current streak and the longest streak within the last year."""
        since = today - timedelta(days=STREAK_WINDOW_DAYS)
        return compute_streak(StatsService.activity_dates(user_id, tz, since=since), today)

    @staticmethod
    def weekly_minutes(user_id, tz, today):
        """
        Study minutes for each of the last 7 local days, oldest first.

        Each entry: date, label (Mon..Sun), minutes, percent of the best day
        (for drawing bars), is_today.
        """
        first_day = today - timedelta(days=6)
        window_start, _ = day_bounds_utc(first_day, tz)
        _, window_end = day_bounds_utc(today, tz)
        rows = db.session.query(StudySession.start_time, StudySession.duration_minutes).filter(
            StudySession.user_id == user_id,
            StudySession.start_time >= window_start,
            StudySession.start_time < window_end,
        ).all()

        totals = {first_day + timedelta(days=n): 0 for n in range(7)}
        for start_time, minutes in rows:
            day = to_local(start_time, tz).date()
            if day in totals:
                totals[day] += minutes or 0

        best = max(totals.values())
        return [
            {
                'date': day,
                'label': day.strftime('%a'),
                'minutes': minutes,
                'percent': round(minutes / best * 100) if best else 0,
                'is_today': day == today,
            }
            for day, minutes in totals.items()
        ]

    @staticmethod
    def pomodoros_on(user_id, tz, day):
        """Completed Pomodoros on one local day."""
        start, end = day_bounds_utc(day, tz)
        return PomodoroSession.query.filter(
            PomodoroSession.user_id == user_id,
            PomodoroSession.completed.is_(True),
            PomodoroSession.start_time >= start,
            PomodoroSession.start_time < end,
        ).count()

    @staticmethod
    def today_tasks(user_id, now_local):
        """
        Open tasks that are overdue or due today.

        Task due dates are stored as the wall-clock time the user typed, so
        they are compared with the user's local time.

        Returns:
            {'items': [(task, 'overdue' | 'today'), ...up to 5], 'total': int, 'more': int}
        """
        end_of_today = datetime.combine(now_local.date() + timedelta(days=1), time.min)
        query = Task.query.filter(
            Task.user_id == user_id,
            Task.status != 'done',
            Task.due_date.isnot(None),
            Task.due_date < end_of_today,
        )
        total = query.count()
        tasks = query.order_by(Task.due_date.asc()).limit(TODAY_TASK_LIMIT).all()
        items = [
            (task, 'overdue' if task.due_date.replace(tzinfo=None) < now_local else 'today')
            for task in tasks
        ]
        return {'items': items, 'total': total, 'more': max(0, total - len(items))}
