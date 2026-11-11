"""Phase 2: server-rendered behaviour of the reworked pages."""

import re
from datetime import datetime
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


def test_card_carries_due_date_for_client_side_overdue_check(auth_client, db_session, test_user):
    """Overdue is decided in the browser, in the user's own timezone."""
    due = datetime(2026, 3, 14, 9, 30)
    task = _add_task(db_session, test_user, title='Timed', status='todo', due_date=due)
    plain = _add_task(db_session, test_user, title='Untimed', status='todo')
    html = auth_client.get('/tasks/').get_data(as_text=True)
    assert 'data-due="2026-03-14T09:30:00"' in _card(html, task.id)
    assert 'data-due' not in _card(html, plain.id)
    assert 'is-overdue' not in html.split('id="main-content"')[1].split('<script')[0]


def test_empty_note_is_hidden_only_in_columns_with_tasks(auth_client, db_session, test_user):
    _add_task(db_session, test_user, title='Only one', status='doing')
    html = auth_client.get('/tasks/').get_data(as_text=True)
    notes = dict(re.findall(r'id="(\w+)-column">.*?<p class="column-empty"( hidden)?>', html, re.S))
    assert notes == {'todo': '', 'doing': ' hidden', 'done': ''}


def test_task_title_is_escaped_in_card(auth_client, db_session, test_user):
    task = _add_task(db_session, test_user, title='<script>alert(1)</script>', status='todo')
    card = _card(auth_client.get('/tasks/').get_data(as_text=True), task.id)
    assert '<script>alert(1)</script>' not in card
    assert '&lt;script&gt;' in card


# --- Schedule --------------------------------------------------------------

def test_schedule_offers_agenda_view(auth_client):
    html = auth_client.get('/calendar/schedule').get_data(as_text=True)
    views = re.findall(r'class="view-btn[^"]*" data-view="(\w+)"', html)
    assert views == ['agenda', 'week', 'month', 'day']
    assert 'id="agendaView"' in html


def test_schedule_tells_script_whether_view_was_requested(auth_client):
    default = auth_client.get('/calendar/schedule').get_data(as_text=True)
    explicit = auth_client.get('/calendar/schedule?view=month').get_data(as_text=True)
    assert '"viewRequested": false' in default
    assert '"viewRequested": true' in explicit


def test_no_stylesheet_makes_body_a_scroll_container():
    """overflow on body breaks the sticky header (see Phase 1 review)."""
    offenders = []
    for path in sorted((STATIC / 'css').rglob('*.css')):
        for selector, body in re.findall(r'([^{}]+)\{([^{}]*)\}', path.read_text()):
            targets = [s.strip() for s in selector.split(',')]
            if 'body' in targets and re.search(r'(?<![-\w])overflow(-[xy])?\s*:', body):
                offenders.append(f'{path.name}: {selector.strip()}')
    assert offenders == []


# --- Dashboard, Pomodoro, stylesheets --------------------------------------

EMOJI = re.compile('[\U0001F300-\U0001FAFF☀-➿⭐⏩-⏿]')


def _main(html):
    return html.split('id="main-content"')[1].split('class="bottom-nav"')[0]


@pytest.mark.parametrize('url', ['/', '/pomodoro/'])
def test_page_uses_icons_not_emoji(auth_client, url):
    content = _main(auth_client.get(url).get_data(as_text=True))
    assert EMOJI.findall(content) == []


def test_dashboard_shows_counts_and_links(auth_client, db_session, test_user):
    _add_task(db_session, test_user, title='One', status='todo')
    _add_task(db_session, test_user, title='Two', status='done')
    content = _main(auth_client.get('/').get_data(as_text=True))
    for label in ('To do', 'In progress', 'Completed', 'Minutes today', 'Decks', 'Flashcards'):
        assert label in content
    assert re.search(r'data-stat="todo"[^>]*>\s*1\s*<', content)
    assert re.search(r'data-stat="done"[^>]*>\s*1\s*<', content)
    assert 'href="/tasks/add"' in content


def test_pomodoro_timer_comes_before_duration_options(auth_client):
    content = _main(auth_client.get('/pomodoro/').get_data(as_text=True))
    assert content.index('id="timer-display"') < content.index('id="start-timer"') < content.index('id="time-25"')


@pytest.mark.parametrize('name', ['kanban.css', 'pomodoro.css', 'decks.css', 'flashcards.css', 'dashboard.css'])
def test_reworked_stylesheet_has_no_hardcoded_hex(name):
    css = (STATIC / 'css' / name).read_text()
    assert HEX.findall(css) == []


@pytest.mark.parametrize('name', ['kanban.css', 'pomodoro.css', 'decks.css', 'flashcards.css', 'dashboard.css'])
def test_reworked_stylesheet_has_no_rgb_literals_except_neutral_shadows(name):
    css = (STATIC / 'css' / name).read_text()
    literals = re.findall(r'rgba?\([^)]*\)', css)
    assert [c for c in literals if not re.match(r'rgba\(0,\s*0,\s*0,', c)] == []


# --- Timezone safety (review findings) ------------------------------------

@pytest.mark.parametrize('name', ['schedule.js', 'calendar/day-view.js', 'calendar/week-view.js',
                                  'calendar/agenda-view.js'])
def test_calendar_scripts_do_not_format_dates_in_utc(name):
    """toISOString() gives the UTC date, which is the wrong day near midnight."""
    js = (STATIC / 'js' / name).read_text()
    assert 'toISOString().split' not in js


def test_agenda_does_not_put_user_data_in_a_style_attribute():
    js = (STATIC / 'js/calendar/agenda-view.js').read_text()
    assert 'style="' not in js
