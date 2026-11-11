"""Installable app: manifest, service worker and offline page."""

import json
from pathlib import Path

STATIC = Path(__file__).resolve().parent.parent / 'app/static'


def test_manifest_is_installable():
    manifest = json.loads((STATIC / 'favicon/site.webmanifest').read_text())
    assert manifest['name'] == 'BrainDump' and manifest['short_name'] == 'BrainDump'
    assert manifest['start_url'] == '/' and manifest['scope'] == '/' and manifest['id'] == '/'
    assert manifest['display'] == 'standalone'
    assert manifest['description']
    sizes = {icon['sizes'] for icon in manifest['icons']}
    assert {'192x192', '512x512'} <= sizes
    for icon in manifest['icons']:
        assert (STATIC.parent / icon['src'].lstrip('/').replace('static/', 'static/', 1)).exists()


def test_service_worker_is_served_from_the_root_without_login(client):
    response = client.get('/sw.js')
    assert response.status_code == 200
    assert response.mimetype in ('text/javascript', 'application/javascript')
    assert response.headers.get('Cache-Control') == 'no-cache'
    body = response.get_data(as_text=True)
    assert '/offline' in body
    assert "request.mode === 'navigate'" in body


def test_service_worker_never_caches_app_pages_or_api_responses():
    source = (STATIC / 'js/sw.js').read_text()
    # only the precache list is ever written to the cache
    assert source.count('cache.put') == 0
    assert source.count('addAll') == 1
    assert "request.method !== 'GET'" in source


def test_offline_page_is_public_and_self_contained(client):
    response = client.get('/offline')
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "You're offline" in html
    assert 'cdnjs' not in html           # must render with no network
    assert 'bottom-nav' not in html      # no app shell that needs a session


def test_app_pages_register_the_service_worker_and_link_the_manifest(auth_client):
    html = auth_client.get('/').get_data(as_text=True)
    assert 'rel="manifest"' in html
    assert 'apple-mobile-web-app-capable' in html or 'mobile-web-app-capable' in html
    script = (STATIC / 'js/common.js').read_text()
    assert "navigator.serviceWorker.register('/sw.js')" in script


def test_login_page_registers_the_service_worker(client):
    assert "serviceWorker.register('/sw.js')" in client.get('/auth/login').get_data(as_text=True)
