"""
The user's timezone, for anything that depends on a calendar day
("today", streaks, the weekly chart).

The browser writes its IANA timezone name into a cookie; the server reads and
validates it here. Timestamps in the database are UTC without tzinfo.
"""

import re
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from flask import has_request_context, request

TZ_COOKIE = 'bd_tz'
UTC = ZoneInfo('UTC')
_ZONE_NAME = re.compile(r'^[A-Za-z][A-Za-z0-9_+\-]*(/[A-Za-z0-9_+\-]+){0,2}$')


def parse_timezone(name):
    """Return the ZoneInfo for a timezone name, or UTC if it is missing or not a real zone."""
    if not name or len(name) > 64 or not _ZONE_NAME.match(name):
        return UTC
    try:
        return ZoneInfo(name)
    except Exception:  # unknown key, or no timezone database on this machine
        return UTC


def get_user_timezone():
    """Timezone of the current request's user (UTC when unknown)."""
    if not has_request_context():
        return UTC
    return parse_timezone(request.cookies.get(TZ_COOKIE, ''))


def to_local(utc_naive, tz):
    """Convert a naive UTC datetime to naive local time in tz."""
    return utc_naive.replace(tzinfo=timezone.utc).astimezone(tz).replace(tzinfo=None)


def local_now(tz, now_utc=None):
    """Current wall-clock time in tz, without tzinfo."""
    now_utc = now_utc or datetime.now(timezone.utc).replace(tzinfo=None)
    return to_local(now_utc, tz)


def day_bounds_utc(local_date, tz):
    """The naive UTC instants at which a local calendar day starts and ends in tz."""
    start_local = datetime.combine(local_date, time.min, tzinfo=tz)
    end_local = datetime.combine(local_date + timedelta(days=1), time.min, tzinfo=tz)
    as_utc = lambda value: value.astimezone(timezone.utc).replace(tzinfo=None)  # noqa: E731
    return as_utc(start_local), as_utc(end_local)
