"""
Slow down password guessing without letting one person lock another out.

Failed sign-ins are stored briefly. Within the window, further attempts are
refused (until the oldest counted failure ages out) when any of these is hit:

- 5 failures for one email from one network address. Someone guessing a
  classmate's password blocks only their own address, not the owner.
- 20 failures for one email across all addresses: stops guessing spread over
  many machines; locking an account this way needs 4+ different addresses.
- 50 failures from one address across all emails: stops one machine trying
  many accounts, with headroom for a class sharing a campus address.

Unknown emails are counted the same way, so the response does not reveal
whether an account exists.
"""

from datetime import timedelta

from app import db
from app.models import LoginAttempt
from app.services.review_service import utcnow

WINDOW = timedelta(minutes=15)
PAIR_LIMIT = 5
EMAIL_LIMIT = 20
IP_LIMIT = 50
KEEP_FOR = timedelta(days=1)


def _normalise(email):
    return (email or '').strip().lower()[:255]


class LoginLimiter:
    """Database-backed sign-in limits (works across several server processes)."""

    @staticmethod
    def _wait_for(filters, limit, now):
        """Seconds until fewer than `limit` matching failures remain in the window."""
        recent = (
            LoginAttempt.query
            .filter(*filters, LoginAttempt.attempted_at > now - WINDOW)
            .order_by(LoginAttempt.attempted_at.desc())
            .limit(limit)
            .all()
        )
        if len(recent) < limit:
            return 0
        oldest = recent[-1].attempted_at
        return (oldest + WINDOW - now).total_seconds()

    @staticmethod
    def seconds_until_allowed(email, ip, now=None):
        """0 if a sign-in may be attempted now, otherwise seconds to wait."""
        now = now or utcnow()
        email = _normalise(email)
        ip = (ip or '')[:64]
        waits = []
        if email:
            waits.append(LoginLimiter._wait_for(
                [LoginAttempt.email == email, LoginAttempt.ip == ip], PAIR_LIMIT, now))
            waits.append(LoginLimiter._wait_for([LoginAttempt.email == email], EMAIL_LIMIT, now))
        if ip:
            waits.append(LoginLimiter._wait_for([LoginAttempt.ip == ip], IP_LIMIT, now))
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
