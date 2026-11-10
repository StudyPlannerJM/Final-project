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
