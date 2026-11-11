"""Sign-in limits, safe redirects after login, password length and production settings."""

from datetime import datetime, timedelta

import pytest
from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix

from app.models import LoginAttempt
from app.services.login_limiter import EMAIL_LIMIT, IP_LIMIT, PAIR_LIMIT, WINDOW, LoginLimiter

NOW = datetime(2026, 11, 11, 12, 0)


# --- Limiter service -------------------------------------------------------

def test_one_address_is_blocked_for_an_email_after_too_many_failures(db_session):
    for _ in range(PAIR_LIMIT - 1):
        LoginLimiter.record_failure('a@b.com', '1.1.1.1', now=NOW)
    assert LoginLimiter.seconds_until_allowed('a@b.com', '1.1.1.1', now=NOW) == 0
    LoginLimiter.record_failure('a@b.com', '1.1.1.1', now=NOW)
    wait = LoginLimiter.seconds_until_allowed('a@b.com', '1.1.1.1', now=NOW)
    assert 0 < wait <= WINDOW.total_seconds()


def test_someone_else_failing_does_not_lock_the_owner_out(db_session):
    """Review finding: a classmate guessing must not block the real owner on another network."""
    for _ in range(PAIR_LIMIT):
        LoginLimiter.record_failure('victim@b.com', '6.6.6.6', now=NOW)
    assert LoginLimiter.seconds_until_allowed('victim@b.com', '1.1.1.1', now=NOW) == 0
    assert LoginLimiter.seconds_until_allowed('other@b.com', '6.6.6.6', now=NOW) == 0


def test_guessing_one_email_from_many_addresses_is_still_limited(db_session):
    for n in range(EMAIL_LIMIT):
        LoginLimiter.record_failure('target@b.com', f'10.0.0.{n}', now=NOW)
    assert LoginLimiter.seconds_until_allowed('target@b.com', '10.0.1.1', now=NOW) > 0


def test_email_is_matched_case_insensitively(db_session):
    for _ in range(PAIR_LIMIT):
        LoginLimiter.record_failure('Student@Study.com', '1.1.1.1', now=NOW)
    assert LoginLimiter.seconds_until_allowed('student@study.com ', '1.1.1.1', now=NOW) > 0


def test_old_failures_stop_counting(db_session):
    for _ in range(PAIR_LIMIT):
        LoginLimiter.record_failure('a@b.com', '1.1.1.1', now=NOW - WINDOW - timedelta(seconds=1))
    assert LoginLimiter.seconds_until_allowed('a@b.com', '1.1.1.1', now=NOW) == 0


def test_address_is_blocked_after_failures_across_many_emails(db_session):
    for n in range(IP_LIMIT):
        LoginLimiter.record_failure(f'user{n}@b.com', '7.7.7.7', now=NOW)
    assert LoginLimiter.seconds_until_allowed('fresh@b.com', '7.7.7.7', now=NOW) > 0
    assert LoginLimiter.seconds_until_allowed('fresh@b.com', '8.8.8.8', now=NOW) == 0


def test_a_busy_shared_network_has_headroom(db_session):
    """A class on one campus address can make a fair number of typos before anyone is blocked."""
    assert IP_LIMIT >= 50
    for n in range(IP_LIMIT - 1):
        LoginLimiter.record_failure(f'student{n}@b.com', '9.9.9.9', now=NOW)
    assert LoginLimiter.seconds_until_allowed('another@b.com', '9.9.9.9', now=NOW) == 0


def test_clear_forgets_an_emails_failures(db_session):
    for _ in range(PAIR_LIMIT):
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
    for _ in range(PAIR_LIMIT):
        _login(client, test_user.email, 'wrong')
    response = _login(client, test_user.email, 'password123')
    assert response.status_code == 429
    assert 'Too many sign-in attempts' in response.get_data(as_text=True)
    assert client.get('/').status_code == 302               # not signed in


def test_unknown_emails_are_limited_the_same_way(client, db_session):
    for _ in range(PAIR_LIMIT):
        _login(client, 'nobody@nowhere.com', 'x')
    assert _login(client, 'nobody@nowhere.com', 'x').status_code == 429


def test_owner_on_another_network_can_still_sign_in(app, test_user):
    attacker = app.test_client()
    for _ in range(PAIR_LIMIT):
        _login(attacker, test_user.email, 'wrong', environ_base={'REMOTE_ADDR': '6.6.6.6'})
    owner = app.test_client()
    response = _login(owner, test_user.email, 'password123', environ_base={'REMOTE_ADDR': '1.2.3.4'})
    assert response.status_code == 302 and response.headers['Location'] == '/dashboard'


def test_successful_sign_in_clears_earlier_failures(client, test_user):
    for _ in range(PAIR_LIMIT - 1):
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


def test_proxy_hops_can_be_configured(monkeypatch):
    from app.security import configure_production
    monkeypatch.setenv('PROXY_FIX_X_FOR', '2')
    app = Flask(__name__)
    configure_production(app)
    assert app.wsgi_app.x_for == 2


def test_the_factory_applies_production_settings(monkeypatch):
    """Review finding: prove create_app('production') really wires them in."""
    import app as app_package
    from app.config import config
    monkeypatch.setattr(config['production'], 'SQLALCHEMY_DATABASE_URI', 'postgresql://u:p@localhost/db')
    monkeypatch.setattr(app_package.db, 'init_app', lambda app: None)        # no database driver needed
    monkeypatch.setattr(app_package.migrate, 'init_app', lambda app, db: None)
    production_app = app_package.create_app('production')
    assert isinstance(production_app.wsgi_app, ProxyFix)
    assert production_app.config['SESSION_COOKIE_SECURE'] is True
    response = production_app.test_client().get('/offline', base_url='https://example.test')
    assert response.headers['Strict-Transport-Security'].startswith('max-age=31536000')


def test_hsts_header_is_sent_when_enabled(app, client, monkeypatch):
    monkeypatch.setitem(app.config, 'BRAINDUMP_HSTS', True)
    assert 'max-age=31536000' in client.get('/auth/login').headers['Strict-Transport-Security']
