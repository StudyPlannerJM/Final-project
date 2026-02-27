import pytest
from app.services.deck_service import DeckService
from app.exceptions import ValidationError, NotFoundError, AuthorizationError
from app.models import Deck


def test_create_deck_valid_and_duplicate(db_session, test_user):
    deck = DeckService.create_deck(test_user.id, 'My Deck', description='d')
    assert isinstance(deck, Deck)
    assert deck.name == 'My Deck'

    # duplicate name should raise
    with pytest.raises(ValidationError):
        DeckService.create_deck(test_user.id, 'My Deck')

    # invalid name
    with pytest.raises(ValidationError):
        DeckService.create_deck(test_user.id, '')


def test_get_user_decks_and_get_by_id(db_session, test_user, test_user_2):
    d1 = DeckService.create_deck(test_user.id, 'A')
    d2 = DeckService.create_deck(test_user.id, 'B')

    decks = DeckService.get_user_decks(test_user.id)
    assert any(d.name == 'A' for d in decks)

    # get by id success
    got = DeckService.get_deck_by_id(d1.id, test_user.id)
    assert got.id == d1.id

    # not found
    with pytest.raises(NotFoundError):
        DeckService.get_deck_by_id(9999, test_user.id)

    # unauthorized
    with pytest.raises(AuthorizationError):
        DeckService.get_deck_by_id(d1.id, test_user_2.id)


def test_update_deck_and_validation(db_session, test_user):
    deck = DeckService.create_deck(test_user.id, 'Old')

    updated = DeckService.update_deck(deck.id, test_user.id, name='New', description='desc', color='#123456', icon='ic')
    assert updated.name == 'New'
    assert updated.description == 'desc'

    # invalid color
    with pytest.raises(ValidationError):
        DeckService.update_deck(deck.id, test_user.id, color='nohash')

    # duplicate name on update
    DeckService.create_deck(test_user.id, 'Other')
    with pytest.raises(ValidationError):
        DeckService.update_deck(deck.id, test_user.id, name='Other')


def test_delete_deck_and_default_protection(db_session, test_user):
    deck = DeckService.create_deck(test_user.id, 'ToDelete')
    DeckService.delete_deck(deck.id, test_user.id)
    # should be gone
    with pytest.raises(NotFoundError):
        DeckService.get_deck_by_id(deck.id, test_user.id)

    # default deck cannot be deleted
    default = DeckService.get_default_deck(test_user.id)
    with pytest.raises(ValidationError):
        DeckService.delete_deck(default.id, test_user.id)


def test_get_or_create_and_get_default(db_session, test_user):
    deck = DeckService.get_or_create_deck(test_user.id, 'AutoDeck')
    assert deck.name == 'AutoDeck'

    # calling again returns same
    deck2 = DeckService.get_or_create_deck(test_user.id, 'AutoDeck')
    assert deck2.id == deck.id

    default = DeckService.get_default_deck(test_user.id)
    assert default.is_default is True
