"""
Slow down password guessing.

Failed sign-ins are stored briefly. Too many for one email address, or from
one IP address, within the window blocks further attempts until the oldest
one in the window ages out. Unknown emails are counted the same way, so the
response does not reveal whether an account exists.
"""

from datetime import timedelta

from app import db
from app.models import LoginAttempt
from app.services.review_service import utcnow

WINDOW = timedelta(minutes=15)
EMAIL_LIMIT = 5
IP_LIMIT = 30
KEEP_FOR = timedelta(days=1)


def _normalise(email):
    return (email or '').strip().lower()[:255]


class LoginLimiter:
    """Database-backed sign-in limits (works across several server processes)."""

    @staticmethod
    def seconds_until_allowed(email, ip, now=None):
        """0 if a sign-in may be attempted now, otherwise seconds to wait."""
        now = now or utcnow()
        since = now - WINDOW
        waits = []
        for column, value, limit in (
            (LoginAttempt.email, _normalise(email), EMAIL_LIMIT),
            (LoginAttempt.ip, (ip or '')[:64], IP_LIMIT),
        ):
            if not value:
                continue
            recent = (
                LoginAttempt.query
                .filter(column == value, LoginAttempt.attempted_at > since)
                .order_by(LoginAttempt.attempted_at.desc())
                .limit(limit)
                .all()
            )
            if len(recent) >= limit:
                # Allowed again once the oldest of the last `limit` failures leaves the window
                oldest = recent[-1].attempted_at
                waits.append((oldest + WINDOW - now).total_seconds())
        return max(0, int(max(waits))) if waits else 0

    @staticmethod
    def record_failure(email, ip, now=None):
        """Store a failed attempt and drop records older than a day."""
        now = now or utcnow()
        LoginAttempt.query.filter(LoginAttempt.attempted_at < now - KEEP_FOR).delete(synchronize_session=False)
        db.session.add(LoginAttempt(email=_normalise(email), ip=(ip or '')[:64], attempted_at=now))
        db.session.commit()

    @staticmethod
    def clear(email):
        """Forget an email's failures after a successful sign-in."""
        LoginAttempt.query.filter(LoginAttempt.email == _normalise(email)).delete(synchronize_session=False)
        db.session.commit()
