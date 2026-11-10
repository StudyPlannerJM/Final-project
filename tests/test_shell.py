"""App shell: theme bootstrap, navigation state and shared layout markup."""

import re

import pytest


def _head(response):
    return response.get_data(as_text=True).split('</head>')[0]


# --- Theme -----------------------------------------------------------------

def test_theme_script_is_inline_in_head_before_stylesheets(auth_client):
    head = _head(auth_client.get('/'))
    assert 'data-theme' in head or 'dataset.theme' in head
    assert 'prefers-color-scheme' in head
    assert head.index('BrainDump') < head.index('variables.css')


def test_theme_script_guards_storage_access(auth_client):
    head = _head(auth_client.get('/'))
    script = head.split('<script>')[1].split('</script>')[0]
    assert 'localStorage' in script
    assert 'try' in script and 'catch' in script


def test_settings_offers_system_theme(auth_client):
    html = auth_client.get('/settings').get_data(as_text=True)
    select = html.split('id="theme-select"')[1].split('</select>')[0]
    for value in ('light', 'dark', 'system'):
        assert f'value="{value}"' in select


# --- Navigation state ------------------------------------------------------

from app.navigation import nav_state, user_initial  # noqa: E402


@pytest.mark.parametrize('bp,ep,item,tab', [
    ('main', 'main.dashboard', 'dashboard', 'home'),
    ('main', 'main.settings', 'settings', 'more'),
    ('tasks', 'tasks.index', 'tasks', 'tasks'),
    ('calendar', 'calendar.schedule', 'schedule', 'schedule'),
    ('pomodoro', 'pomodoro.index', 'pomodoro', 'study'),
    ('flashcards', 'flashcards.index', 'flashcards', 'study'),
    ('summarizer', 'summarizer.index', 'summarizer', 'more'),
    ('ai_planner', 'ai_planner.generator', 'ai_planner', 'more'),
    ('admin', 'admin.manage_users', 'admin', 'more'),
    (None, None, None, None),
    ('auth', 'auth.login', None, None),
])
def test_nav_state(bp, ep, item, tab):
    assert nav_state(bp, ep) == {'item': item, 'tab': tab}


@pytest.mark.parametrize('name,expected', [
    ('marcos', 'M'), ('  ana', 'A'), ('élodie', 'É'), ('日本', '日'),
    ('', '?'), ('   ', '?'), (None, '?'),
])
def test_user_initial(name, expected):
    assert user_initial(name) == expected


# --- Shell markup ----------------------------------------------------------

PAGES = [
    ('/', 'home'), ('/tasks/', 'tasks'), ('/pomodoro/', 'study'),
    ('/flashcards/', 'study'), ('/summarizer/', 'more'), ('/settings', 'more'),
]


def _bottom_nav(html):
    return html.split('class="bottom-nav"')[1].split('</nav>')[0]


@pytest.mark.parametrize('url,tab', PAGES)
def test_page_renders_bottom_nav_with_active_tab(auth_client, url, tab):
    response = auth_client.get(url, follow_redirects=True)
    assert response.status_code == 200
    nav = _bottom_nav(response.get_data(as_text=True))
    active = re.findall(r'<(?:a|button)\b[^>]*\bis-active\b[^>]*>', nav)
    assert len(active) == 1
    assert f'data-tab="{tab}"' in active[0]


def test_bottom_nav_has_five_tabs_in_order(auth_client):
    nav = _bottom_nav(auth_client.get('/').get_data(as_text=True))
    assert re.findall(r'data-tab="(\w+)"', nav) == ['home', 'tasks', 'schedule', 'study', 'more']


def test_sheet_tabs_are_buttons_wired_to_their_sheets(auth_client):
    html = auth_client.get('/').get_data(as_text=True)
    for name in ('study', 'more'):
        assert re.search(rf'<button[^>]*aria-controls="sheet-{name}"', html)
        assert re.search(rf'<div[^>]*id="sheet-{name}"[^>]*hidden', html)


def test_exactly_one_sidebar_item_is_current(auth_client):
    html = auth_client.get('/tasks/').get_data(as_text=True)
    sidebar = html.split('class="sidebar"')[1].split('</nav>')[0]
    assert sidebar.count('aria-current="page"') == 1
    current = re.search(r'<a[^>]*aria-current="page"[^>]*>', sidebar).group(0)
    assert '/tasks/' in current


def test_unknown_url_is_404_not_500(auth_client):
    assert auth_client.get('/no-such-page').status_code == 404


def test_manage_users_only_for_admins(auth_client, db_session, test_user):
    assert 'Manage Users' not in auth_client.get('/').get_data(as_text=True)
    test_user.is_admin = True
    db_session.session.commit()
    assert 'Manage Users' in auth_client.get('/').get_data(as_text=True)


def test_shell_has_no_third_party_avatar_or_bg_shapes(auth_client):
    html = auth_client.get('/').get_data(as_text=True)
    assert 'ui-avatars.com' not in html
    assert 'dashboard-bg-shape' not in html


def test_avatar_shows_user_initial(auth_client):
    html = auth_client.get('/').get_data(as_text=True)
    assert re.search(r'class="avatar"[^>]*>\s*T\s*<', html)


def test_skip_link_targets_main_content(auth_client):
    html = auth_client.get('/').get_data(as_text=True)
    assert 'class="skip-link" href="#main-content"' in html
    assert 'id="main-content"' in html


def test_flash_renders_as_toast(auth_client):
    with auth_client.session_transaction() as sess:
        sess['_flashes'] = [('success', 'Saved'), ('danger', 'Broken')]
    html = auth_client.get('/').get_data(as_text=True)
    assert 'class="toast toast--success"' in html
    assert 'class="toast toast--danger"' in html
    assert html.count('toast__close') == 2
