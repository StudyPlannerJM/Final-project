import pytest
from app.services.study_plan_service import StudyPlanService
from app.models import StudyPlan
from app.exceptions import ValidationError, NotFoundError, AuthorizationError


def test_create_plan_success(db_session, test_user, monkeypatch):
    monkeypatch.setattr(
        'app.services.study_plan_service.generate_study_plan',
        lambda subject, time_value, time_unit, knowledge_level: 'A' * 200
    )

    plan = StudyPlanService.create_plan(
        user_id=test_user.id,
        subject='Physics',
        time_value=4,
        time_unit='weeks',
        knowledge_level='beginner'
    )

    assert isinstance(plan, StudyPlan)
    assert plan.user_id == test_user.id
    assert 'A' * 200 == plan.plan_content


def test_create_plan_user_not_found(db_session):
    with pytest.raises(NotFoundError):
        StudyPlanService.create_plan(99999, 'Math', 1, 'days', 'beginner')


@pytest.mark.parametrize('subject', ['', 'A'])
def test_create_plan_invalid_subject_short(db_session, test_user, subject):
    with pytest.raises(ValidationError):
        StudyPlanService.create_plan(test_user.id, subject, 1, 'days', 'beginner')


def test_create_plan_subject_too_long(db_session, test_user):
    long_subject = 'x' * 101
    with pytest.raises(ValidationError):
        StudyPlanService.create_plan(test_user.id, long_subject, 1, 'days', 'beginner')


def test_create_plan_invalid_time_value(db_session, test_user):
    with pytest.raises(ValidationError):
        StudyPlanService.create_plan(test_user.id, 'Bio', 0, 'days', 'beginner')

    with pytest.raises(ValidationError):
        StudyPlanService.create_plan(test_user.id, 'Bio', 366, 'days', 'beginner')


def test_create_plan_invalid_time_unit(db_session, test_user):
    with pytest.raises(ValidationError):
        StudyPlanService.create_plan(test_user.id, 'Bio', 5, 'years', 'beginner')


def test_create_plan_invalid_knowledge_level(db_session, test_user):
    with pytest.raises(ValidationError):
        StudyPlanService.create_plan(test_user.id, 'Bio', 5, 'days', 'expert')


def test_create_plan_generation_error(db_session, test_user, monkeypatch):
    def raise_exc(*a, **k):
        raise Exception('API down')

    monkeypatch.setattr('app.services.study_plan_service.generate_study_plan', raise_exc)

    with pytest.raises(ValidationError):
        StudyPlanService.create_plan(test_user.id, 'Chem', 3, 'days', 'beginner')


def test_delete_get_and_list_plans(db_session, test_user, test_user_2):
    # create two plans for test_user
    p1 = StudyPlan(user_id=test_user.id, subject='S1', time_value=1, time_unit='days', knowledge_level='beginner', plan_content='content1')
    p2 = StudyPlan(user_id=test_user.id, subject='S2', time_value=2, time_unit='weeks', knowledge_level='intermediate', plan_content='content2')
    db_session.session.add_all([p1, p2])
    db_session.session.commit()

    plans = StudyPlanService.get_user_plans(test_user.id)
    assert len(plans) >= 2

    # get single plan
    got = StudyPlanService.get_plan(p1.id, test_user.id)
    assert got.id == p1.id

    # authorization check
    with pytest.raises(AuthorizationError):
        StudyPlanService.get_plan(p1.id, test_user_2.id)

    # delete plan
    StudyPlanService.delete_plan(p1.id, test_user.id)
    with pytest.raises(NotFoundError):
        StudyPlanService.get_plan(p1.id, test_user.id)
