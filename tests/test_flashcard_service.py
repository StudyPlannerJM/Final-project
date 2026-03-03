import pytest
from app.services.flashcard_service import FlashcardService
from app.exceptions import ValidationError, NotFoundError, AuthorizationError
from app.models import Deck, Flashcard


def create_deck_for_user(db_session, test_user, name='Default'):
    deck = Deck(name=name, user_id=test_user.id, description='d')
    db_session.session.add(deck)
    db_session.session.commit()
    db_session.session.refresh(deck)
    return deck


def test_create_flashcard_uses_default_deck(db_session, test_user, monkeypatch):
    deck = create_deck_for_user(db_session, test_user, name='DefaultDeck')

    monkeypatch.setattr('app.services.flashcard_service.DeckService.get_default_deck', lambda uid: deck)

    fc = FlashcardService.create_flashcard(test_user.id, 'Q?', 'A.', deck_id=None)
    assert isinstance(fc, Flashcard)
    assert fc.question == 'Q?'
    assert fc.answer == 'A.'
    assert fc.deck_id == deck.id


def test_create_flashcard_validation_errors(test_user):
    with pytest.raises(ValidationError):
        FlashcardService.create_flashcard(test_user.id, '', 'A')

    with pytest.raises(ValidationError):
        FlashcardService.create_flashcard(test_user.id, 'Q', '')


def test_get_flashcard_by_id_and_authorization(db_session, test_user, test_user_2):
    # create a flashcard for user1
    fc = Flashcard(question='Q', answer='A', user_id=test_user.id)
    db_session.session.add(fc)
    db_session.session.commit()
    db_session.session.refresh(fc)

    # user1 can access
    got = FlashcardService.get_flashcard_by_id(fc.id, test_user.id)
    assert got.id == fc.id

    # user2 cannot
    with pytest.raises(AuthorizationError):
        FlashcardService.get_flashcard_by_id(fc.id, test_user_2.id)

    # nonexistent
    with pytest.raises(NotFoundError):
        FlashcardService.get_flashcard_by_id(99999, test_user.id)


def test_update_flashcard_and_change_deck(db_session, test_user, monkeypatch):
    deck1 = create_deck_for_user(db_session, test_user, name='One')
    deck2 = create_deck_for_user(db_session, test_user, name='Two')

    fc = Flashcard(question='Old', answer='OldA', user_id=test_user.id, deck_id=deck1.id)
    db_session.session.add(fc)
    db_session.session.commit()
    db_session.session.refresh(fc)

    # ensure DeckService.get_deck_by_id will succeed when changing deck
    monkeypatch.setattr('app.services.flashcard_service.DeckService.get_deck_by_id', lambda did, uid: deck2)

    updated = FlashcardService.update_flashcard(fc.id, test_user.id, question='NewQ', answer='NewA', deck_id=deck2.id)
    assert updated.question == 'NewQ'
    assert updated.answer == 'NewA'
    assert updated.deck_id == deck2.id


def test_delete_flashcard(db_session, test_user):
    fc = Flashcard(question='T', answer='A', user_id=test_user.id)
    db_session.session.add(fc)
    db_session.session.commit()
    db_session.session.refresh(fc)

    FlashcardService.delete_flashcard(fc.id, test_user.id)

    assert db_session.session.get(Flashcard, fc.id) is None


def test_get_user_flashcards_filters(db_session, test_user):
    deck = Deck(name='D', user_id=test_user.id)
    db_session.session.add(deck)
    db_session.session.commit()
    db_session.session.refresh(deck)

    f1 = Flashcard(question='A', answer='a', user_id=test_user.id, deck_id=deck.id)
    f2 = Flashcard(question='B', answer='b', user_id=test_user.id)
    db_session.session.add_all([f1, f2])
    db_session.session.commit()

    all_f = FlashcardService.get_user_flashcards(test_user.id)
    assert len(all_f) >= 2

    deck_f = FlashcardService.get_user_flashcards(test_user.id, deck_id=deck.id)
    assert all(getattr(f, 'deck_id') == deck.id for f in deck_f)


def test_bulk_create_flashcards_success_and_errors(db_session, test_user, monkeypatch):
    deck = create_deck_for_user(db_session, test_user, name='Bulk')
    monkeypatch.setattr('app.services.flashcard_service.DeckService.get_default_deck', lambda uid: deck)

    data = [
        {'question': 'Q1', 'answer': 'A1'},
        {'question': 'Q2', 'answer': 'A2'},
    ]

    created = FlashcardService.bulk_create_flashcards(test_user.id, data)
    assert len(created) == 2

    # empty data => ValidationError
    with pytest.raises(ValidationError):
        FlashcardService.bulk_create_flashcards(test_user.id, [])

    # missing fields
    with pytest.raises(ValidationError):
        FlashcardService.bulk_create_flashcards(test_user.id, [{'question': '', 'answer': 'A'}])
