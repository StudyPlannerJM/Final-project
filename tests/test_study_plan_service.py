import pytest
from datetime import datetime, timezone
from app.services.study_plan_service import StudyPlanService
from app.models import StudyPlan, Category
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


def test_create_tasks_from_plan_success_with_due_date_distribution(db_session, test_user):
    plan = StudyPlan(
        user_id=test_user.id,
        subject='Physics',
        time_value=2,
        time_unit='weeks',
        knowledge_level='beginner',
        plan_content='''
## Milestones
- Review Newton laws
- Solve 20 practice problems
- Summarize key formulas
''',
        created_at=datetime(2026, 3, 1, tzinfo=timezone.utc)
    )
    db_session.session.add(plan)
    db_session.session.commit()

    created = StudyPlanService.create_tasks_from_plan(plan, test_user.id, num_tasks=3)

    assert len(created) == 3
    assert all(task.user_id == test_user.id for task in created)
    assert all(task.due_date is not None for task in created)
    assert created[0].due_date < created[1].due_date < created[2].due_date

    category = Category.query.filter_by(user_id=test_user.id, name='Study Plan: Physics').first()
    assert category is not None
    assert all(task.category_id == category.id for task in created)


def test_create_tasks_from_plan_rejects_invalid_count(db_session, test_user):
    plan = StudyPlan(
        user_id=test_user.id,
        subject='Math',
        time_value=1,
        time_unit='weeks',
        knowledge_level='beginner',
        plan_content='- Task one'
    )
    db_session.session.add(plan)
    db_session.session.commit()

    with pytest.raises(ValidationError):
        StudyPlanService.create_tasks_from_plan(plan, test_user.id, num_tasks=0)

    with pytest.raises(ValidationError):
        StudyPlanService.create_tasks_from_plan(plan, test_user.id, num_tasks=6)


def test_create_tasks_from_plan_authorization_check(db_session, test_user, test_user_2):
    plan = StudyPlan(
        user_id=test_user.id,
        subject='Chemistry',
        time_value=1,
        time_unit='weeks',
        knowledge_level='beginner',
        plan_content='- Study atomic structure'
    )
    db_session.session.add(plan)
    db_session.session.commit()

    with pytest.raises(AuthorizationError):
        StudyPlanService.create_tasks_from_plan(plan, test_user_2.id, num_tasks=1)


def test_extract_task_candidates_uses_multiple_patterns():
    plan_content = '''
## Weekly Plan
Week 1: Learn variables and loops
- Build a small calculator app
1. Practice 15 coding exercises
* [ ] Review function examples
'''

    tasks = StudyPlanService._extract_task_candidates(plan_content)

    assert 'Learn variables and loops' in tasks
    assert 'Build a small calculator app' in tasks
    assert 'Practice 15 coding exercises' in tasks
    assert 'Review function examples' in tasks
