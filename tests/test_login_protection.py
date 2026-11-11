"""Sign-in limits, safe redirects after login, password length and production settings."""

from datetime import datetime, timedelta

import pytest
from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix

from app.models import LoginAttempt
from app.services.login_limiter import EMAIL_LIMIT, IP_LIMIT, WINDOW, LoginLimiter

NOW = datetime(2026, 11, 11, 12, 0)


# --- Limiter service -------------------------------------------------------

def test_email_is_blocked_after_too_many_failures(db_session):
    for _ in range(EMAIL_LIMIT - 1):
        LoginLimiter.record_failure('a@b.com', '1.1.1.1', now=NOW)
    assert LoginLimiter.seconds_until_allowed('a@b.com', '2.2.2.2', now=NOW) == 0
    LoginLimiter.record_failure('a@b.com', '1.1.1.1', now=NOW)
    wait = LoginLimiter.seconds_until_allowed('a@b.com', '2.2.2.2', now=NOW)
    assert 0 < wait <= WINDOW.total_seconds()
    assert LoginLimiter.seconds_until_allowed('other@b.com', '2.2.2.2', now=NOW) == 0


def test_email_is_matched_case_insensitively(db_session):
    for _ in range(EMAIL_LIMIT):
        LoginLimiter.record_failure('Student@Study.com', '1.1.1.1', now=NOW)
    assert LoginLimiter.seconds_until_allowed('student@study.com ', '9.9.9.9', now=NOW) > 0


def test_old_failures_stop_counting(db_session):
    for _ in range(EMAIL_LIMIT):
        LoginLimiter.record_failure('a@b.com', '1.1.1.1', now=NOW - WINDOW - timedelta(seconds=1))
    assert LoginLimiter.seconds_until_allowed('a@b.com', '1.1.1.1', now=NOW) == 0


def test_ip_is_blocked_after_failures_across_many_emails(db_session):
    for n in range(IP_LIMIT):
        LoginLimiter.record_failure(f'user{n}@b.com', '7.7.7.7', now=NOW)
    assert LoginLimiter.seconds_until_allowed('fresh@b.com', '7.7.7.7', now=NOW) > 0
    assert LoginLimiter.seconds_until_allowed('fresh@b.com', '8.8.8.8', now=NOW) == 0


def test_clear_forgets_an_emails_failures(db_session):
    for _ in range(EMAIL_LIMIT):
        LoginLimiter.record_failure('a@b.com', '1.1.1.1', now=NOW)
    LoginLimiter.clear('A@b.com')
    assert LoginLimiter.seconds_until_allowed('a@b.com', '1.1.1.1', now=NOW) == 0


def test_rows_older_than_a_day_are_pruned(db_session):
    LoginLimiter.record_failure('old@b.com', '1.1.1.1', now=NOW - timedelta(days=2))
    LoginLimiter.record_failure('new@b.com', '1.1.1.1', now=NOW)
    assert [a.email for a in LoginAttempt.query.all()] == ['new@b.com']


# --- Login route -----------------------------------------------------------

def _login(client, email, password, **kwargs):
    return client.post('/auth/login', data={'email': email, 'password': password}, **kwargs)


def test_locked_out_even_with_the_right_password(client, test_user):
    for _ in range(EMAIL_LIMIT):
        _login(client, test_user.email, 'wrong')
    response = _login(client, test_user.email, 'password123')
    assert response.status_code == 429
    assert 'Too many sign-in attempts' in response.get_data(as_text=True)
    assert client.get('/').status_code == 302               # not signed in


def test_unknown_emails_are_limited_the_same_way(client, db_session):
    for _ in range(EMAIL_LIMIT):
        _login(client, 'nobody@nowhere.com', 'x')
    assert _login(client, 'nobody@nowhere.com', 'x').status_code == 429


def test_successful_sign_in_clears_earlier_failures(client, test_user):
    for _ in range(EMAIL_LIMIT - 1):
        _login(client, test_user.email, 'wrong')
    _login(client, test_user.email, 'password123')
    assert LoginAttempt.query.filter_by(email=test_user.email.lower()).count() == 0


@pytest.mark.parametrize('target,expected', [
    ('/tasks/', '/tasks/'),
    ('/flashcards/review?deck_id=2', '/flashcards/review?deck_id=2'),
    ('https://evil.example/', '/dashboard'),
    ('//evil.example/', '/dashboard'),
    ('/\\evil.example', '/dashboard'),
    ('javascript:alert(1)', '/dashboard'),
    ('', '/dashboard'),
])
def test_next_is_only_followed_within_the_site(client, test_user, target, expected):
    response = _login(client, test_user.email, 'password123', query_string={'next': target})
    assert response.status_code == 302
    assert response.headers['Location'] == expected


# --- Password length ------------------------------------------------------

def test_registration_needs_eight_characters(client, db_session):
    response = client.post('/auth/register', data={
        'username': 'shorty', 'email': 'short@example.com',
        'password': 'abc1234', 'password2': 'abc1234'})
    assert response.status_code == 200
    assert 'at least 8 characters' in response.get_data(as_text=True)


def test_admin_user_form_needs_eight_characters():
    from app.forms import AdminCreateUserForm, AdminEditUserForm
    for form_class in (AdminCreateUserForm, AdminEditUserForm):
        lengths = [v for v in form_class.password.kwargs['validators'] if v.__class__.__name__ == 'Length']
        assert lengths and lengths[0].min == 8, form_class.__name__


# --- Production settings ---------------------------------------------------

def test_production_settings_secure_cookies_and_trust_one_proxy():
    from app.security import configure_production
    app = Flask(__name__)
    configure_production(app)
    assert app.config['SESSION_COOKIE_SECURE'] is True
    assert app.config['REMEMBER_COOKIE_SECURE'] is True
    assert isinstance(app.wsgi_app, ProxyFix)
    assert app.wsgi_app.x_for == 1
    assert app.config['BRAINDUMP_HSTS'] is True
