"""
Spaced repetition: the scheduler and the queries around it.

The scheduler is a simplified SM-2. It is a pure function so it can be tested
with a fixed clock; ReviewService wraps it with database access.
All datetimes are UTC without tzinfo, matching how the database stores them.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import case, func, or_

from app import db
from app.exceptions import NotFoundError, ValidationError
from app.models import CardReview, Deck, Flashcard

AGAIN, HARD, GOOD, EASY = 0, 1, 2, 3
RATINGS = (AGAIN, HARD, GOOD, EASY)

MIN_EASE = 1.3
DEFAULT_EASE = 2.5
MAX_INTERVAL_DAYS = 365
RELEARN_DELAY = timedelta(minutes=10)
MASTERED_INTERVAL_DAYS = 21
SESSION_LIMIT = 50


@dataclass(frozen=True)
class CardState:
    """The part of a flashcard the scheduler reads and writes."""
    interval_days: int
    ease: float
    reps: int
    lapses: int


def utcnow():
    """Current UTC time without tzinfo (the form the database stores)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def schedule(state, rating, now):
    """
    Work out a card's next state and due time after a review.

    Args:
        state: CardState before the review
        rating: AGAIN, HARD, GOOD or EASY
        now: time of the review (UTC, naive)

    Returns:
        (CardState, due_at)

    Raises:
        ValidationError: if rating is not one of the four ratings
    """
    if isinstance(rating, bool) or not isinstance(rating, int) or rating not in RATINGS:
        raise ValidationError('Rating must be 0 (again), 1 (hard), 2 (good) or 3 (easy)')

    ease = state.ease
    if rating == AGAIN:
        new_state = CardState(
            interval_days=0,
            ease=max(MIN_EASE, ease - 0.20),
            reps=0,
            lapses=state.lapses + 1,
        )
        return new_state, now + RELEARN_DELAY

    hard, good, easy = _success_intervals(state)
    if rating == HARD:
        interval = hard
        ease = max(MIN_EASE, ease - 0.15)
    elif rating == GOOD:
        interval = good
    else:  # EASY
        interval = easy
        ease = ease + 0.15

    interval = max(1, min(MAX_INTERVAL_DAYS, interval))
    new_state = CardState(interval_days=interval, ease=ease, reps=state.reps + 1, lapses=state.lapses)
    return new_state, now + timedelta(days=interval)


def _success_intervals(state):
    """
    Next interval in days for Hard, Good and Easy.

    Kept in order (Hard <= Good <= Easy) so a harder answer never earns a
    longer gap, and a successful review of a card already in progress always
    moves it further out than its current interval.
    """
    if state.reps == 0:
        hard, good, easy = 1, 1, 4
    else:
        current = max(state.interval_days, 1)
        good = 3 if state.reps == 1 else round(current * state.ease)
        good = max(good, current + 1)
        hard = max(current + 1, round(current * 1.2))
        easy = round(current * state.ease * 1.3)
    hard = min(hard, good)
    easy = max(easy, good + 1) if state.reps else easy
    cap = lambda days: max(1, min(MAX_INTERVAL_DAYS, days))  # noqa: E731
    return cap(hard), cap(good), cap(easy)


def stage_of(last_reviewed_at, interval_days):
    """'new' (never reviewed), 'learning' or 'mastered' (interval of 21 days or more)."""
    if last_reviewed_at is None:
        return 'new'
    return 'mastered' if interval_days >= MASTERED_INTERVAL_DAYS else 'learning'


def describe_interval(delta):
    """Short human text for a timedelta: '10 min', '1 day', '3 days', '2 months'."""
    minutes = int(delta.total_seconds() // 60)
    if minutes < 1:
        return 'less than a minute'
    if minutes < 60:
        return f'{minutes} min'
    days = delta.days
    if days < 1:
        hours = minutes // 60
        return f'{hours} hour' + ('' if hours == 1 else 's')
    if days < 30:
        return f'{days} day' + ('' if days == 1 else 's')
    months = round(days / 30)
    if months < 12:
        return f'{months} month' + ('' if months == 1 else 's')
    return '1 year'


def _state_of(card):
    return CardState(
        interval_days=card.interval_days or 0,
        ease=card.ease or DEFAULT_EASE,
        reps=card.reps or 0,
        lapses=card.lapses or 0,
    )


class ReviewService:
    """Database-backed operations for reviewing flashcards."""

    @staticmethod
    def _due_filter(now):
        return or_(Flashcard.due_at.is_(None), Flashcard.due_at <= now)

    @staticmethod
    def get_due_cards(user_id, deck_id=None, now=None, limit=SESSION_LIMIT):
        """
        Cards to review now: overdue cards first (most overdue first),
        then cards that have never been reviewed (oldest first).
        """
        now = now or utcnow()
        query = Flashcard.query.filter(Flashcard.user_id == user_id, ReviewService._due_filter(now))
        if deck_id is not None:
            query = query.filter(Flashcard.deck_id == deck_id)
        never_reviewed_last = case((Flashcard.due_at.is_(None), 1), else_=0)
        return query.order_by(never_reviewed_last, Flashcard.due_at.asc(), Flashcard.id.asc()).limit(limit).all()

    @staticmethod
    def count_due(user_id, deck_id=None, now=None):
        """Number of cards due now."""
        now = now or utcnow()
        query = db.session.query(func.count(Flashcard.id)).filter(
            Flashcard.user_id == user_id, ReviewService._due_filter(now)
        )
        if deck_id is not None:
            query = query.filter(Flashcard.deck_id == deck_id)
        return query.scalar() or 0

    @staticmethod
    def next_due_at(user_id, deck_id=None, now=None):
        """When the next card becomes due, or None if nothing is scheduled."""
        now = now or utcnow()
        query = db.session.query(func.min(Flashcard.due_at)).filter(
            Flashcard.user_id == user_id, Flashcard.due_at > now
        )
        if deck_id is not None:
            query = query.filter(Flashcard.deck_id == deck_id)
        return query.scalar()

    @staticmethod
    def record_review(flashcard_id, user_id, rating, now=None):
        """
        Apply a rating to a card and log it.

        Raises:
            NotFoundError: the card does not exist or belongs to someone else
            ValidationError: the rating is not valid
        """
        now = now or utcnow()
        card = Flashcard.query.filter_by(id=flashcard_id, user_id=user_id).first()
        if card is None:
            raise NotFoundError('Flashcard not found')

        new_state, due_at = schedule(_state_of(card), rating, now)
        card.interval_days = new_state.interval_days
        card.ease = new_state.ease
        card.reps = new_state.reps
        card.lapses = new_state.lapses
        card.due_at = due_at
        card.last_reviewed_at = now
        db.session.add(CardReview(user_id=user_id, flashcard_id=card.id, rating=rating, reviewed_at=now))
        db.session.commit()
        return card

    @staticmethod
    def preview(card):
        """What each rating would do to this card, as short text keyed by rating."""
        state = _state_of(card)
        anchor = datetime(2000, 1, 1)
        return {rating: describe_interval(schedule(state, rating, anchor)[1] - anchor) for rating in RATINGS}

    @staticmethod
    def deck_progress(user_id, now=None):
        """
        Per deck: total cards, how many are new / learning / mastered, and how many are due.
        One grouped query, so it stays cheap with many cards.
        """
        now = now or utcnow()
        no_card = Flashcard.id.is_(None)        # the outer join row of an empty deck
        is_new = Flashcard.last_reviewed_at.is_(None)
        is_mastered = Flashcard.interval_days >= MASTERED_INTERVAL_DAYS
        rows = (
            db.session.query(
                Deck.id, Deck.name, Deck.color,
                func.count(Flashcard.id),
                func.coalesce(func.sum(case((no_card, 0), (is_new, 1), else_=0)), 0),
                func.coalesce(func.sum(case((no_card, 0), (is_new, 0), (is_mastered, 1), else_=0)), 0),
                func.coalesce(func.sum(case((no_card, 0), (ReviewService._due_filter(now), 1), else_=0)), 0),
            )
            .outerjoin(Flashcard, (Flashcard.deck_id == Deck.id) & (Flashcard.user_id == user_id))
            .filter(Deck.user_id == user_id)
            .group_by(Deck.id, Deck.name, Deck.color)
            .order_by(Deck.name.asc())
            .all()
        )
        return [
            {
                'deck_id': deck_id, 'name': name, 'color': color, 'total': total,
                'new': int(new), 'learning': int(total - new - mastered),
                'mastered': int(mastered), 'due': int(due),
            }
            for deck_id, name, color, total, new, mastered, due in rows
        ]
