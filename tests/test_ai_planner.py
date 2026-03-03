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
