import datetime
from types import SimpleNamespace

def make_deck(name='Deck', flashcard_count=0):
    class FC:
        def __init__(self, cnt):
            self._cnt = cnt
        def count(self):
            return self._cnt

    return SimpleNamespace(id=1, name=name, flashcards=FC(flashcard_count), created_at=datetime.datetime.now())


def test_decks_renders(monkeypatch, auth_client, test_user):
    deck = make_deck('MyDeck', 3)
    monkeypatch.setattr('app.routes.flashcards.DeckService.get_user_decks', lambda uid: [deck])

    resp = auth_client.get('/flashcards/decks')
    assert resp.status_code == 200
    assert b'MyDeck' in resp.data


def test_add_deck_post_success(monkeypatch, auth_client, test_user):
    monkeypatch.setattr('app.routes.flashcards.DeckService.create_deck', lambda **kw: SimpleNamespace(name=kw.get('name')))

    data = {'name': 'New Deck', 'description': 'd', 'color': '#fff', 'icon': 'fa'}
    resp = auth_client.post('/flashcards/add_deck', data=data, follow_redirects=False)
    assert resp.status_code in (302, 303)


def test_add_deck_validation_error(monkeypatch, auth_client, test_user):
    from app.exceptions import ValidationError
    def raise_val(**kw):
        raise ValidationError('Bad deck')

    monkeypatch.setattr('app.routes.flashcards.DeckService.create_deck', raise_val)
    data = {'name': 'X', 'description': '', 'color': '#fff', 'icon': ''}
    resp = auth_client.post('/flashcards/add_deck', data=data, follow_redirects=True)
    assert resp.status_code == 200
    assert b'Bad deck' in resp.data


def test_delete_deck_success_and_error(monkeypatch, auth_client, test_user):
    deck = make_deck('D', 2)
    monkeypatch.setattr('app.routes.flashcards.DeckService.get_deck_by_id', lambda deck_id, uid: deck)
    monkeypatch.setattr('app.routes.flashcards.DeckService.delete_deck', lambda deck_id, uid: None)

    resp = auth_client.post('/flashcards/delete_deck/1', follow_redirects=False)
    assert resp.status_code in (302, 303)

    # simulate not found
    from app.exceptions import NotFoundError
    def raise_nf(did, uid):
        raise NotFoundError('Missing')

    monkeypatch.setattr('app.routes.flashcards.DeckService.get_deck_by_id', raise_nf)
    resp = auth_client.post('/flashcards/delete_deck/1', follow_redirects=True)
    assert resp.status_code == 200
    assert b'Missing' in resp.data


def test_index_no_deck_shows_grid(monkeypatch, auth_client, test_user):
    deck = make_deck('GridDeck', 0)
    monkeypatch.setattr('app.routes.flashcards.DeckService.get_user_decks', lambda uid: [deck])

    resp = auth_client.get('/flashcards/')
    assert resp.status_code == 200
    assert b'GridDeck' in resp.data


def test_index_with_deck_selected(monkeypatch, auth_client, test_user):
    deck = make_deck('SelDeck', 0)
    flashcard = SimpleNamespace(id=1, question='Q1', answer='A1', deck_id=deck.id, deck=deck)
    monkeypatch.setattr('app.routes.flashcards.DeckService.get_user_decks', lambda uid: [deck])
    monkeypatch.setattr('app.routes.flashcards.DeckService.get_deck_by_id', lambda did, uid: deck)
    monkeypatch.setattr('app.routes.flashcards.FlashcardService.get_user_flashcards', lambda uid, deck_id=None: [flashcard])

    resp = auth_client.get(f'/flashcards/?deck_id={deck.id}')
    assert resp.status_code == 200
    assert b'Q1' in resp.data


def test_add_flashcard_get_prefill(monkeypatch, auth_client, test_user):
    deck = make_deck('Prefill', 0)
    monkeypatch.setattr('app.routes.flashcards.DeckService.get_deck_by_id', lambda did, uid: deck)

    resp = auth_client.get(f'/flashcards/add?deck_id={deck.id}')
    assert resp.status_code == 200


def test_add_flashcard_post_success(monkeypatch, auth_client, test_user):
    monkeypatch.setattr('app.routes.flashcards.FlashcardService.create_flashcard', lambda **kw: SimpleNamespace(deck_id=kw.get('deck_id')))
    # Force form to validate and provide data without relying on QuerySelectField plumbing
    monkeypatch.setattr('app.routes.flashcards.FlashcardForm.validate_on_submit', lambda self: True)
    monkeypatch.setattr('app.routes.flashcards.FlashcardForm.question', SimpleNamespace(data='Q'))
    monkeypatch.setattr('app.routes.flashcards.FlashcardForm.answer', SimpleNamespace(data='A'))
    monkeypatch.setattr('app.routes.flashcards.FlashcardForm.deck', SimpleNamespace(data=SimpleNamespace(id=1)))

    resp = auth_client.post('/flashcards/add', data={}, follow_redirects=False)
    assert resp.status_code in (302, 303)


def test_edit_flashcard_get_and_post(monkeypatch, auth_client, test_user):
    flashcard = SimpleNamespace(id=2, question='OldQ', answer='OldA', deck=SimpleNamespace(id=1), deck_id=1)
    monkeypatch.setattr('app.routes.flashcards.FlashcardService.get_flashcard_by_id', lambda fid, uid: flashcard)
    monkeypatch.setattr('app.routes.flashcards.FlashcardService.update_flashcard', lambda **kw: None)

    resp = auth_client.get(f'/flashcards/edit/{flashcard.id}')
    assert resp.status_code == 200

    # Patch form validation and fields for POST
    monkeypatch.setattr('app.routes.flashcards.FlashcardForm.validate_on_submit', lambda self: True)
    monkeypatch.setattr('app.routes.flashcards.FlashcardForm.question', SimpleNamespace(data='NewQ'))
    monkeypatch.setattr('app.routes.flashcards.FlashcardForm.answer', SimpleNamespace(data='NewA'))
    monkeypatch.setattr('app.routes.flashcards.FlashcardForm.deck', SimpleNamespace(data=SimpleNamespace(id=1)))

    resp = auth_client.post(f'/flashcards/edit/{flashcard.id}', data={}, follow_redirects=False)
    assert resp.status_code in (302, 303)


def test_delete_flashcard_success_and_error(monkeypatch, auth_client, test_user):
    flashcard = SimpleNamespace(id=3, deck_id=5)
    monkeypatch.setattr('app.routes.flashcards.FlashcardService.get_flashcard_by_id', lambda fid, uid: flashcard)
    monkeypatch.setattr('app.routes.flashcards.FlashcardService.delete_flashcard', lambda fid, uid: None)

    resp = auth_client.post(f'/flashcards/delete/{flashcard.id}', follow_redirects=False)
    assert resp.status_code in (302, 303)

    from app.exceptions import AuthorizationError
    def raise_auth(fid, uid):
        raise AuthorizationError('Denied')

    monkeypatch.setattr('app.routes.flashcards.FlashcardService.get_flashcard_by_id', lambda fid, uid: flashcard)
    monkeypatch.setattr('app.routes.flashcards.FlashcardService.delete_flashcard', raise_auth)
    resp = auth_client.post(f'/flashcards/delete/{flashcard.id}', follow_redirects=True)
    assert resp.status_code == 200
    assert b'Denied' in resp.data


def test_generate_from_study_plan_unauthorized(db_session, auth_client, test_user, test_user_2):
    from app.models import StudyPlan
    # create plan for other user
    p = StudyPlan(user_id=test_user_2.id, subject='S', time_value=1, time_unit='days', knowledge_level='beginner', plan_content='C')
    db_session.session.add(p)
    db_session.session.commit()

    resp = auth_client.post(f'/flashcards/generate_from_study_plan/{p.id}', data={'num_cards': '5'}, follow_redirects=True)
    assert resp.status_code == 200
    assert b'not authorized' in resp.data.lower()


def test_generate_from_study_plan_without_ai_configured(monkeypatch, db_session, auth_client, test_user):
    from app.models import StudyPlan
    from app.utils.ai_generator import NOT_CONFIGURED_MESSAGE
    p = StudyPlan(user_id=test_user.id, subject='S', time_value=1, time_unit='days', knowledge_level='beginner', plan_content='C')
    db_session.session.add(p)
    db_session.session.commit()

    # The test app has no Gemini key, so the real helper reports it is not set up
    resp = auth_client.post(f'/flashcards/generate_from_study_plan/{p.id}', data={'num_cards': '5'}, follow_redirects=True)
    assert resp.status_code == 200
    assert NOT_CONFIGURED_MESSAGE in resp.get_data(as_text=True)


def test_generate_from_study_plan_success(monkeypatch, db_session, auth_client, test_user):
    from app.models import StudyPlan
    p = StudyPlan(user_id=test_user.id, subject='S', time_value=1, time_unit='days', knowledge_level='beginner', plan_content='Q\nA')
    db_session.session.add(p)
    db_session.session.commit()

    monkeypatch.setattr('app.routes.flashcards.generate_text', lambda prompt: 'Q: What?\nA: That.')
    deck = SimpleNamespace(id=99, name='S')
    monkeypatch.setattr('app.routes.flashcards.DeckService.get_or_create_deck', lambda **kw: deck)
    monkeypatch.setattr('app.routes.flashcards.FlashcardService.bulk_create_flashcards', lambda **kw: [{'id':1}])

    resp = auth_client.post(f'/flashcards/generate_from_study_plan/{p.id}', data={'num_cards': '1'}, follow_redirects=False)
    assert resp.status_code in (302, 303)
    assert resp.headers['Location'].endswith('/flashcards/?deck_id=99')
