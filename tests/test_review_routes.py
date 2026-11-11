"""Review session routes and the timezone helper."""

import json
import re
from datetime import datetime, timedelta

import pytest

from app.models import CardReview, Deck, Flashcard
from app.services.review_service import utcnow
from app.utils.timezone import TZ_COOKIE, day_bounds_utc, get_user_timezone, to_local


@pytest.fixture
def deck(db_session, test_user):
    deck = Deck(name='Biology', user_id=test_user.id)
    db_session.session.add(deck)
    db_session.session.commit()
    return deck


def _card(db_session, user, deck, question='Q', **fields):
    card = Flashcard(question=question, answer='A', user_id=user.id, deck_id=deck.id)
    for name, value in fields.items():
        setattr(card, name, value)
    db_session.session.add(card)
    db_session.session.commit()
    return card


def _session_cards(html):
    raw = re.search(r'<script type="application/json" id="review-data">(.*?)</script>', html, re.S).group(1)
    return json.loads(raw)


# --- Review page -----------------------------------------------------------

def test_review_page_lists_only_due_cards_of_the_user(auth_client, db_session, test_user, test_user_2, deck):
    due = _card(db_session, test_user, deck, 'due card')
    _card(db_session, test_user, deck, 'later', due_at=utcnow() + timedelta(days=3),
          last_reviewed_at=utcnow(), interval_days=3, reps=2)
    other = Deck(name='Theirs', user_id=test_user_2.id)
    db_session.session.add(other)
    db_session.session.commit()
    _card(db_session, test_user_2, other, 'not mine')

    response = auth_client.get('/flashcards/review')
    assert response.status_code == 200
    data = _session_cards(response.get_data(as_text=True))
    assert [c['id'] for c in data['cards']] == [due.id]
    card = data['cards'][0]
    assert card['question'] == 'due card' and card['answer'] == 'A' and card['deck'] == 'Biology'
    assert card['preview'] == {'0': '10 min', '1': '1 day', '2': '1 day', '3': '4 days'}
    assert card['version'] == '0-0'


def test_review_page_escapes_card_text_inside_json(auth_client, db_session, test_user, deck):
    _card(db_session, test_user, deck, '</script><script>alert(1)</script>')
    html = auth_client.get('/flashcards/review').get_data(as_text=True)
    assert '</script><script>alert(1)' not in html
    assert _session_cards(html)['cards'][0]['question'] == '</script><script>alert(1)</script>'


def test_review_page_with_nothing_due_says_caught_up(auth_client, db_session, test_user, deck):
    _card(db_session, test_user, deck, 'later', due_at=utcnow() + timedelta(days=3),
          last_reviewed_at=utcnow(), interval_days=3, reps=2)
    html = auth_client.get('/flashcards/review').get_data(as_text=True)
    assert _session_cards(html)['cards'] == []
    assert 'All caught up' in html


def test_review_page_for_someone_elses_deck_is_not_found(auth_client, db_session, test_user_2):
    other = Deck(name='Theirs', user_id=test_user_2.id)
    db_session.session.add(other)
    db_session.session.commit()
    assert auth_client.get(f'/flashcards/review?deck_id={other.id}', follow_redirects=False).status_code == 404


def test_review_requires_login(client):
    assert client.get('/flashcards/review').status_code == 302


# --- Rating ----------------------------------------------------------------

def _rate(client, card_id, rating, version='0-0'):
    return client.post(f'/flashcards/review/{card_id}', json={'rating': rating, 'version': version})


def test_rating_updates_card_and_logs_review(auth_client, db_session, test_user, deck):
    card = _card(db_session, test_user, deck)
    response = _rate(auth_client, card.id, 2)
    assert response.status_code == 200
    body = response.get_json()
    assert body['success'] is True and body['due_in'] == '1 day' and body['version'] == '1-0'
    assert body['preview'] == {'0': '10 min', '1': '2 days', '2': '3 days', '3': '3 days'}
    db_session.session.refresh(card)
    assert card.reps == 1 and card.interval_days == 1
    assert CardReview.query.filter_by(flashcard_id=card.id, rating=2).count() == 1


@pytest.mark.parametrize('payload', [{'rating': 7, 'version': '0-0'}, {'rating': 'good', 'version': '0-0'},
                                     {'version': '0-0'}, {}])
def test_invalid_rating_is_rejected_without_changes(auth_client, db_session, test_user, deck, payload):
    card = _card(db_session, test_user, deck)
    response = auth_client.post(f'/flashcards/review/{card.id}', json=payload)
    assert response.status_code == 400 and response.get_json()['success'] is False
    assert CardReview.query.count() == 0


def test_replayed_rating_is_a_conflict_and_is_not_applied_twice(auth_client, db_session, test_user, deck):
    card = _card(db_session, test_user, deck)
    assert _rate(auth_client, card.id, 2).status_code == 200
    replay = _rate(auth_client, card.id, 2)
    assert replay.status_code == 409
    db_session.session.refresh(card)
    assert card.reps == 1 and CardReview.query.count() == 1


def test_rating_another_users_card_is_not_found(auth_client, db_session, test_user_2):
    other = Deck(name='Theirs', user_id=test_user_2.id)
    db_session.session.add(other)
    db_session.session.commit()
    card = _card(db_session, test_user_2, other)
    assert _rate(auth_client, card.id, 2).status_code == 404
    assert CardReview.query.count() == 0


def test_rating_a_deleted_card_is_not_found(auth_client):
    assert _rate(auth_client, 999999, 2).status_code == 404


def test_rating_requires_csrf_token_when_protection_is_on(app, auth_client, db_session, test_user, deck):
    card = _card(db_session, test_user, deck)
    app.config['WTF_CSRF_ENABLED'] = True
    try:
        assert _rate(auth_client, card.id, 2).status_code == 400
        html = auth_client.get('/flashcards/review').get_data(as_text=True)
        token = re.search(r'<meta name="csrf-token" content="([^"]+)"', html).group(1)
        ok = auth_client.post(f'/flashcards/review/{card.id}', json={'rating': 2, 'version': '0-0'},
                              headers={'X-CSRFToken': token})
        assert ok.status_code == 200
    finally:
        app.config['WTF_CSRF_ENABLED'] = False


def test_flashcards_page_offers_review_with_due_count(auth_client, db_session, test_user, deck):
    _card(db_session, test_user, deck, 'one')
    _card(db_session, test_user, deck, 'two')
    html = auth_client.get('/flashcards/').get_data(as_text=True)
    assert 'href="/flashcards/review"' in html
    assert re.search(r'Review due cards\s*<span[^>]*>2<', html)


# --- Timezone helper -------------------------------------------------------

@pytest.mark.parametrize('value,expected', [
    ('America/Sao_Paulo', 'America/Sao_Paulo'), ('Europe/Dublin', 'Europe/Dublin'),
    ('', 'UTC'), ('Not/AZone', 'UTC'), ('../../etc/passwd', 'UTC'), ('a' * 300, 'UTC'),
    ('Europe/Dublin DROP', 'UTC'), ('Europe/Dublin/../x', 'UTC'),
])
def test_timezone_cookie_is_validated(app, value, expected):
    headers = {'Cookie': f'{TZ_COOKIE}={value}'} if value else {}
    with app.test_request_context('/', headers=headers):
        assert get_user_timezone().key == expected


def test_to_local_and_day_bounds_follow_the_zone(app):
    from zoneinfo import ZoneInfo
    sao_paulo = ZoneInfo('America/Sao_Paulo')  # UTC-3, no DST
    assert to_local(datetime(2026, 11, 12, 1, 30), sao_paulo) == datetime(2026, 11, 11, 22, 30)
    start, end = day_bounds_utc(datetime(2026, 11, 11).date(), sao_paulo)
    assert (start, end) == (datetime(2026, 11, 11, 3, 0), datetime(2026, 11, 12, 3, 0))


def test_theme_bootstrap_sets_timezone_cookie(auth_client):
    head = auth_client.get('/').get_data(as_text=True).split('</head>')[0]
    assert 'bd_tz=' in head and 'resolvedOptions().timeZone' in head
