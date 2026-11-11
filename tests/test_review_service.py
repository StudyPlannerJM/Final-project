"""Spaced repetition: scheduler maths and the review service."""

from datetime import datetime, timedelta

import pytest

from app.exceptions import NotFoundError, ValidationError
from app.models import CardReview, Deck, Flashcard
from app.services.review_service import (
    AGAIN, EASY, GOOD, HARD, MAX_INTERVAL_DAYS, MIN_EASE, CardState, ReviewService, schedule, stage_of,
)

NOW = datetime(2026, 11, 11, 12, 0, 0)
NEW = CardState(interval_days=0, ease=2.5, reps=0, lapses=0)


# --- Pure scheduler --------------------------------------------------------

def test_again_on_new_card_comes_back_in_ten_minutes():
    state, due = schedule(NEW, AGAIN, NOW)
    assert due == NOW + timedelta(minutes=10)
    assert (state.reps, state.lapses, state.interval_days) == (0, 1, 0)
    assert state.ease == pytest.approx(2.3)


@pytest.mark.parametrize('rating,days', [(HARD, 1), (GOOD, 1), (EASY, 4)])
def test_first_successful_review_intervals(rating, days):
    state, due = schedule(NEW, rating, NOW)
    assert state.interval_days == days
    assert due == NOW + timedelta(days=days)
    assert state.reps == 1


def test_good_progression_is_one_three_then_times_ease():
    state, _ = schedule(NEW, GOOD, NOW)
    state, _ = schedule(state, GOOD, NOW)
    assert state.interval_days == 3
    state, _ = schedule(state, GOOD, NOW)
    assert state.interval_days == round(3 * 2.5)


def test_hard_grows_slowly_but_always_by_at_least_a_day():
    mature = CardState(interval_days=10, ease=2.5, reps=4, lapses=0)
    state, _ = schedule(mature, HARD, NOW)
    assert state.interval_days == 12
    assert state.ease == pytest.approx(2.35)
    short = CardState(interval_days=1, ease=2.5, reps=1, lapses=0)
    assert schedule(short, HARD, NOW)[0].interval_days == 2


def test_easy_grows_fastest_and_raises_ease():
    mature = CardState(interval_days=10, ease=2.5, reps=4, lapses=0)
    state, _ = schedule(mature, EASY, NOW)
    assert state.interval_days == round(10 * 2.5 * 1.3)
    assert state.ease == pytest.approx(2.65)


def test_again_on_mature_card_resets_progress_and_counts_a_lapse():
    mature = CardState(interval_days=40, ease=2.5, reps=6, lapses=1)
    state, due = schedule(mature, AGAIN, NOW)
    assert (state.reps, state.lapses, state.interval_days) == (0, 2, 0)
    assert due == NOW + timedelta(minutes=10)


def test_ease_never_drops_below_floor():
    state = CardState(interval_days=5, ease=MIN_EASE, reps=3, lapses=0)
    for rating in (AGAIN, HARD):
        assert schedule(state, rating, NOW)[0].ease == pytest.approx(MIN_EASE)


def test_interval_is_capped():
    huge = CardState(interval_days=300, ease=2.5, reps=9, lapses=0)
    assert schedule(huge, EASY, NOW)[0].interval_days == MAX_INTERVAL_DAYS


@pytest.mark.parametrize('rating', [-1, 4, 'good', None, 2.5, True])
def test_invalid_rating_is_rejected(rating):
    with pytest.raises(ValidationError):
        schedule(NEW, rating, NOW)


@pytest.mark.parametrize('reviewed,interval,expected', [
    (False, 0, 'new'), (True, 0, 'learning'), (True, 20, 'learning'), (True, 21, 'mastered'),
])
def test_stage_of(reviewed, interval, expected):
    assert stage_of(NOW if reviewed else None, interval) == expected


# --- Service ---------------------------------------------------------------

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


def test_new_cards_are_due_and_future_cards_are_not(db_session, test_user, deck):
    fresh = _card(db_session, test_user, deck, 'fresh')
    overdue = _card(db_session, test_user, deck, 'overdue', due_at=NOW - timedelta(days=2),
                    last_reviewed_at=NOW - timedelta(days=5), interval_days=3, reps=2)
    _card(db_session, test_user, deck, 'later', due_at=NOW + timedelta(days=2),
          last_reviewed_at=NOW, interval_days=2, reps=2)
    due = ReviewService.get_due_cards(test_user.id, now=NOW)
    assert [c.id for c in due] == [overdue.id, fresh.id]
    assert ReviewService.count_due(test_user.id, now=NOW) == 2


def test_due_cards_can_be_limited_to_a_deck_and_never_leak_other_users(db_session, test_user, test_user_2, deck):
    mine = _card(db_session, test_user, deck, 'mine')
    other_deck = Deck(name='Other', user_id=test_user.id)
    theirs_deck = Deck(name='Theirs', user_id=test_user_2.id)
    db_session.session.add_all([other_deck, theirs_deck])
    db_session.session.commit()
    _card(db_session, test_user, other_deck, 'elsewhere')
    _card(db_session, test_user_2, theirs_deck, 'not mine')
    assert [c.id for c in ReviewService.get_due_cards(test_user.id, deck_id=deck.id, now=NOW)] == [mine.id]
    assert ReviewService.count_due(test_user.id, now=NOW) == 2


def test_record_review_updates_card_and_writes_log(db_session, test_user, deck):
    card = _card(db_session, test_user, deck)
    ReviewService.record_review(card.id, test_user.id, GOOD, now=NOW)
    db_session.session.refresh(card)
    assert card.due_at == NOW + timedelta(days=1)
    assert (card.reps, card.interval_days, card.last_reviewed_at) == (1, 1, NOW)
    log = CardReview.query.filter_by(flashcard_id=card.id).all()
    assert [(r.user_id, r.rating, r.reviewed_at) for r in log] == [(test_user.id, GOOD, NOW)]


def test_record_review_refuses_other_users_cards(db_session, test_user, test_user_2, deck):
    card = _card(db_session, test_user, deck)
    with pytest.raises(NotFoundError):
        ReviewService.record_review(card.id, test_user_2.id, GOOD, now=NOW)
    assert CardReview.query.count() == 0


def test_deleting_a_card_removes_its_review_log(db_session, test_user, deck):
    card = _card(db_session, test_user, deck)
    ReviewService.record_review(card.id, test_user.id, GOOD, now=NOW)
    db_session.session.delete(card)
    db_session.session.commit()
    assert CardReview.query.count() == 0


def test_deck_progress_counts_stages_and_due(db_session, test_user, deck):
    _card(db_session, test_user, deck, 'new')
    _card(db_session, test_user, deck, 'learning', due_at=NOW + timedelta(days=3),
          last_reviewed_at=NOW, interval_days=3, reps=2)
    _card(db_session, test_user, deck, 'mastered due', due_at=NOW - timedelta(days=1),
          last_reviewed_at=NOW - timedelta(days=31), interval_days=30, reps=6)
    progress = ReviewService.deck_progress(test_user.id, now=NOW)
    assert progress == [{'deck_id': deck.id, 'name': 'Biology', 'color': deck.color, 'total': 3,
                         'new': 1, 'learning': 1, 'mastered': 1, 'due': 2}]


def test_preview_intervals_describe_each_rating(db_session, test_user, deck):
    card = _card(db_session, test_user, deck)
    assert ReviewService.preview(card) == {AGAIN: '10 min', HARD: '1 day', GOOD: '1 day', EASY: '4 days'}


# --- Review fixes: ratings stay in order ----------------------------------

def _reachable_states(depth=5):
    """Every card state reachable from a new card in up to `depth` ratings."""
    frontier = {NEW}
    seen = set(frontier)
    for _ in range(depth):
        nxt = set()
        for state in frontier:
            for rating in (AGAIN, HARD, GOOD, EASY):
                nxt.add(schedule(state, rating, NOW)[0])
        frontier = nxt - seen
        seen |= nxt
    return seen


def test_harder_answers_never_earn_longer_intervals():
    for state in _reachable_states():
        hard = schedule(state, HARD, NOW)[0].interval_days
        good = schedule(state, GOOD, NOW)[0].interval_days
        easy = schedule(state, EASY, NOW)[0].interval_days
        assert hard <= good <= easy, state
        if state.reps > 0:
            assert good > state.interval_days or good == MAX_INTERVAL_DAYS, state


def test_easy_then_good_does_not_shrink_the_interval():
    state, _ = schedule(NEW, EASY, NOW)          # 4 days
    assert schedule(state, GOOD, NOW)[0].interval_days > 4


def test_describe_interval_under_a_minute():
    from app.services.review_service import describe_interval
    assert describe_interval(timedelta(seconds=20)) == 'less than a minute'


def test_deck_progress_includes_empty_decks(db_session, test_user, deck):
    empty = Deck(name='Empty', user_id=test_user.id)
    db_session.session.add(empty)
    db_session.session.commit()
    rows = {row['name']: row for row in ReviewService.deck_progress(test_user.id, now=NOW)}
    assert rows['Empty'] == {'deck_id': empty.id, 'name': 'Empty', 'color': empty.color, 'total': 0,
                             'new': 0, 'learning': 0, 'mastered': 0, 'due': 0}
