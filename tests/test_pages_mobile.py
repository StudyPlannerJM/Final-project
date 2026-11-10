"""Phase 2: server-rendered behaviour of the reworked pages."""

import re
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from app.models import Task

STATIC = Path(__file__).resolve().parent.parent / 'app/static'
HEX = re.compile(r'#[0-9a-fA-F]{3,8}\b')


def _add_task(db_session, user, **kwargs):
    task = Task(user_id=user.id, **kwargs)
    db_session.session.add(task)
    db_session.session.commit()
    return task


def _card(html, task_id):
    marker = html.index(f'data-task-id="{task_id}"')
    start = html.rindex('<article', 0, marker)
    return html[start:html.index('</article>', marker)]


# --- Tasks board -----------------------------------------------------------

def test_board_has_three_columns_with_tabs(auth_client):
    html = auth_client.get('/tasks/').get_data(as_text=True)
    assert re.findall(r'class="column-content" data-status="(\w+)"', html) == ['todo', 'doing', 'done']
    assert re.findall(r'class="board-tab[^"]*"[^>]*data-status="(\w+)"', html) == ['todo', 'doing', 'done']


@pytest.mark.parametrize('status,others', [
    ('todo', ['doing', 'done']),
    ('doing', ['todo', 'done']),
    ('done', ['todo', 'doing']),
])
def test_card_move_control_lists_the_other_statuses(auth_client, db_session, test_user, status, others):
    task = _add_task(db_session, test_user, title='Movable', status=status)
    card = _card(auth_client.get('/tasks/').get_data(as_text=True), task.id)
    select = card.split('class="task-move"')[1].split('</select>')[0]
    assert re.findall(r'<option value="(\w+)"', select) == others
    assert 'aria-label="Move task' in card


def test_empty_column_shows_empty_state(auth_client):
    html = auth_client.get('/tasks/').get_data(as_text=True)
    assert html.count('class="column-empty"') == 3


def test_overdue_open_task_is_marked(auth_client, db_session, test_user):
    late = _add_task(db_session, test_user, title='Late', status='todo',
                     due_date=datetime.now() - timedelta(days=1))
    html = auth_client.get('/tasks/').get_data(as_text=True)
    assert 'is-overdue' in _card(html, late.id)
    assert 'Overdue' in _card(html, late.id)


def test_done_or_future_task_is_not_marked_overdue(auth_client, db_session, test_user):
    finished = _add_task(db_session, test_user, title='Finished', status='done',
                         due_date=datetime.now() - timedelta(days=1))
    upcoming = _add_task(db_session, test_user, title='Upcoming', status='todo',
                         due_date=datetime.now() + timedelta(days=1))
    html = auth_client.get('/tasks/').get_data(as_text=True)
    assert 'is-overdue' not in _card(html, finished.id)
    assert 'is-overdue' not in _card(html, upcoming.id)


def test_task_title_is_escaped_in_card(auth_client, db_session, test_user):
    task = _add_task(db_session, test_user, title='<script>alert(1)</script>', status='todo')
    card = _card(auth_client.get('/tasks/').get_data(as_text=True), task.id)
    assert '<script>alert(1)</script>' not in card
    assert '&lt;script&gt;' in card
