from types import SimpleNamespace


def test_generator_get_shows_previous_plans(monkeypatch, auth_client, test_user):
    import datetime
    sample = SimpleNamespace(id=1, subject='Math', created_at=datetime.datetime.now(), time_value=3, time_unit='weeks', knowledge_level='beginner')
    monkeypatch.setattr('app.routes.ai_planner.StudyPlanService.get_user_plans', lambda uid, limit=5: [sample])

    resp = auth_client.get('/ai-planner/generator')
    assert resp.status_code == 200
    assert b'Math' in resp.data


def test_generator_post_creates_and_redirects(monkeypatch, auth_client, test_user):
    fake_plan = SimpleNamespace(id=77)
    monkeypatch.setattr('app.routes.ai_planner.StudyPlanService.create_plan', lambda **kw: fake_plan)

    data = {
        'subject': 'Physics',
        'time_value': '4',
        'time_unit': 'weeks',
        'knowledge_level': 'beginner'
    }

    resp = auth_client.post('/ai-planner/generator', data=data, follow_redirects=False)
    assert resp.status_code in (302, 303)
    assert f'/ai-planner/view/{fake_plan.id}' in resp.headers.get('Location', '')


def test_generator_post_handles_validation_error(monkeypatch, auth_client, test_user):
    def raise_val(**kw):
        from app.exceptions import ValidationError
        raise ValidationError('Bad input')

    monkeypatch.setattr('app.routes.ai_planner.StudyPlanService.create_plan', raise_val)

    # send VALID form data so the route calls the service and the service raises
    data = {
        'subject': 'Physics',
        'time_value': '4',
        'time_unit': 'weeks',
        'knowledge_level': 'beginner'
    }

    resp = auth_client.post('/ai-planner/generator', data=data, follow_redirects=True)
    assert resp.status_code == 200
    assert b'Bad input' in resp.data


def test_view_plan_renders_formatted_content(monkeypatch, auth_client, test_user):
    import datetime
    sample = SimpleNamespace(id=5, subject='Chem', plan_content='raw', created_at=datetime.datetime.now(), time_value=2, time_unit='weeks', knowledge_level='beginner')
    monkeypatch.setattr('app.routes.ai_planner.StudyPlanService.get_plan', lambda pid, uid: sample)
    monkeypatch.setattr('app.routes.ai_planner.format_plan_for_display', lambda c: '<p>formatted</p>')

    resp = auth_client.get(f'/ai-planner/view/{sample.id}')
    assert resp.status_code == 200
    assert b'formatted' in resp.data


def test_view_plan_handles_not_found(monkeypatch, auth_client):
    def raise_nf(pid, uid):
        from app.exceptions import NotFoundError
        raise NotFoundError('No plan')

    monkeypatch.setattr('app.routes.ai_planner.StudyPlanService.get_plan', raise_nf)

    resp = auth_client.get('/ai-planner/view/999', follow_redirects=True)
    assert resp.status_code == 200
    assert b'No plan' in resp.data


def test_my_plans_shows_list(monkeypatch, auth_client, test_user):
    import datetime
    sample = SimpleNamespace(id=2, subject='Bio', created_at=datetime.datetime.now(), time_value=1, time_unit='days', knowledge_level='beginner')
    monkeypatch.setattr('app.routes.ai_planner.StudyPlanService.get_user_plans', lambda uid: [sample])

    resp = auth_client.get('/ai-planner/my-plans')
    assert resp.status_code == 200
    assert b'Bio' in resp.data


def test_delete_plan_success_and_error(monkeypatch, auth_client, test_user):
    # success
    monkeypatch.setattr('app.routes.ai_planner.StudyPlanService.delete_plan', lambda pid, uid: None)
    resp = auth_client.post('/ai-planner/delete/1', follow_redirects=False)
    assert resp.status_code in (302, 303)

    # error
    def raise_auth(pid, uid):
        from app.exceptions import AuthorizationError
        raise AuthorizationError('Denied')

    monkeypatch.setattr('app.routes.ai_planner.StudyPlanService.delete_plan', raise_auth)
    resp = auth_client.post('/ai-planner/delete/1', follow_redirects=True)
    assert resp.status_code == 200
    assert b'Denied' in resp.data


def test_generate_tasks_from_plan_success(monkeypatch, auth_client, test_user):
    import datetime
    sample = SimpleNamespace(
        id=11,
        user_id=test_user.id,
        subject='Math',
        plan_content='- One',
        created_at=datetime.datetime.now(),
        time_value=2,
        time_unit='weeks',
        knowledge_level='beginner'
    )
    monkeypatch.setattr('app.routes.ai_planner.StudyPlanService.get_plan', lambda pid, uid: sample)
    monkeypatch.setattr('app.routes.ai_planner.format_plan_for_display', lambda c: '<p>x</p>')
    monkeypatch.setattr(
        'app.routes.ai_planner.StudyPlanService.create_tasks_from_plan',
        lambda plan, user_id, num_tasks: [SimpleNamespace(id=1), SimpleNamespace(id=2)]
    )

    resp = auth_client.post('/ai-planner/generate_tasks/11', data={'num_tasks': '2'}, follow_redirects=True)
    assert resp.status_code == 200
    assert b'Created 2 task(s) from your study plan!' in resp.data


def test_generate_tasks_from_plan_invalid_count(monkeypatch, auth_client, test_user):
    import datetime
    sample = SimpleNamespace(
        id=13,
        user_id=test_user.id,
        subject='Math',
        plan_content='- One',
        created_at=datetime.datetime.now(),
        time_value=2,
        time_unit='weeks',
        knowledge_level='beginner'
    )
    monkeypatch.setattr('app.routes.ai_planner.StudyPlanService.get_plan', lambda pid, uid: sample)
    monkeypatch.setattr('app.routes.ai_planner.format_plan_for_display', lambda c: '<p>x</p>')

    resp = auth_client.post('/ai-planner/generate_tasks/13', data={'num_tasks': 'abc'}, follow_redirects=True)
    assert resp.status_code == 200
    assert b'Number of tasks must be a valid number' in resp.data


def test_generate_tasks_from_plan_no_candidates(monkeypatch, auth_client, test_user):
    import datetime
    sample = SimpleNamespace(
        id=14,
        user_id=test_user.id,
        subject='Math',
        plan_content='- One',
        created_at=datetime.datetime.now(),
        time_value=2,
        time_unit='weeks',
        knowledge_level='beginner'
    )
    monkeypatch.setattr('app.routes.ai_planner.StudyPlanService.get_plan', lambda pid, uid: sample)
    monkeypatch.setattr('app.routes.ai_planner.format_plan_for_display', lambda c: '<p>x</p>')
    monkeypatch.setattr(
        'app.routes.ai_planner.StudyPlanService.create_tasks_from_plan',
        lambda plan, user_id, num_tasks: []
    )

    resp = auth_client.post('/ai-planner/generate_tasks/14', data={'num_tasks': '5'}, follow_redirects=True)
    assert resp.status_code == 200
    assert b'No actionable items were found in this plan to create tasks.' in resp.data


def test_generate_tasks_from_plan_handles_authorization(monkeypatch, auth_client):
    def raise_auth(pid, uid):
        from app.exceptions import AuthorizationError
        raise AuthorizationError('Denied')

    monkeypatch.setattr('app.routes.ai_planner.StudyPlanService.get_plan', raise_auth)

    resp = auth_client.post('/ai-planner/generate_tasks/99', data={'num_tasks': '5'}, follow_redirects=True)
    assert resp.status_code == 200
    assert b'Denied' in resp.data


# --- AI service failures (review of a live 503) ----------------------------

def test_failed_generation_saves_nothing_and_says_why(monkeypatch, auth_client, test_user):
    from app.models import StudyPlan
    from app.utils.ai_generator import AIServiceError

    def busy(*args, **kwargs):
        raise AIServiceError('The AI service is busy right now. Please try again in a minute.')

    monkeypatch.setattr('app.services.study_plan_service.generate_study_plan', busy)
    response = auth_client.post('/ai-planner/generator', data={
        'subject': 'Chemistry', 'time_value': 3, 'time_unit': 'days', 'knowledge_level': 'beginner'},
        follow_redirects=True)
    html = response.get_data(as_text=True)
    assert 'The AI service is busy right now' in html
    assert 'generated successfully' not in html
    assert StudyPlan.query.filter_by(user_id=test_user.id).count() == 0


def test_failed_flashcard_generation_leaves_no_empty_deck(monkeypatch, auth_client, db_session, test_user):
    from app.models import Deck, StudyPlan
    from app.utils.ai_generator import AIServiceError

    plan = StudyPlan(user_id=test_user.id, subject='Physics', time_value=3, time_unit='days',
                     knowledge_level='beginner', plan_content='# Overview\n- Forces and motion basics')
    db_session.session.add(plan)
    db_session.session.commit()

    def busy(*args, **kwargs):
        raise AIServiceError('The AI service is busy right now. Please try again in a minute.')

    monkeypatch.setattr('app.routes.flashcards.generate_text', busy)
    response = auth_client.post(f'/flashcards/generate_from_study_plan/{plan.id}',
                                data={'num_cards': 5}, follow_redirects=True)
    assert 'The AI service is busy right now' in response.get_data(as_text=True)
    assert Deck.query.filter_by(user_id=test_user.id, name='Physics').count() == 0


def test_flashcard_generation_uses_the_shared_ai_call(monkeypatch, auth_client, db_session, test_user):
    from app.models import Flashcard, StudyPlan

    plan = StudyPlan(user_id=test_user.id, subject='Biology', time_value=3, time_unit='days',
                     knowledge_level='beginner', plan_content='# Overview\n- Cells')
    db_session.session.add(plan)
    db_session.session.commit()
    monkeypatch.setattr('app.routes.flashcards.generate_text',
                        lambda prompt: 'Q: What is a cell?\nA: The basic unit of life.')
    auth_client.post(f'/flashcards/generate_from_study_plan/{plan.id}', data={'num_cards': 1})
    assert Flashcard.query.filter_by(user_id=test_user.id).count() == 1
