import io
import datetime
from types import SimpleNamespace
from app.exceptions import NotFoundError, AuthorizationError


def test_index_shows_user_summaries(monkeypatch, auth_client, test_user):
    sample = SimpleNamespace(
        id=1,
        title='Test Title',
        file_type='pdf',
        summary_text='Short summary text',
        original_filename='file.pdf',
        date_created=datetime.datetime(2021, 1, 1)
    )

    monkeypatch.setattr(
        'app.routes.summarizer.SummaryService.get_user_summaries',
        lambda user_id: [sample]
    )

    resp = auth_client.get('/summarizer/')
    assert resp.status_code == 200
    assert b'Test Title' in resp.data


def test_index_handles_not_found(monkeypatch, auth_client):
    # Ensure url_for used by the route can be built in the test runner
    monkeypatch.setattr('app.routes.summarizer.url_for', lambda *a, **k: '/')

    def raise_nf(uid):
        raise NotFoundError('No user')

    monkeypatch.setattr(
        'app.routes.summarizer.SummaryService.get_user_summaries',
        raise_nf
    )

    resp = auth_client.get('/summarizer/', follow_redirects=True)
    assert resp.status_code == 200
    assert b'No user' in resp.data


def test_view_summary_success(monkeypatch, auth_client):
    sample = SimpleNamespace(
        id=2,
        title='View Title',
        summary_text='The summary',
        extracted_text='Original text',
        original_filename='file.docx',
        file_type='word',
        date_created=datetime.datetime.now()
    )

    monkeypatch.setattr(
        'app.routes.summarizer.SummaryService.get_summary',
        lambda summary_id, user_id: sample
    )

    resp = auth_client.get('/summarizer/view/2')
    assert resp.status_code == 200
    assert b'View Title' in resp.data
    assert b'The summary' in resp.data


def test_view_handles_errors(monkeypatch, auth_client):
    def raise_auth(sid, uid):
        raise AuthorizationError('No permission')

    monkeypatch.setattr(
        'app.routes.summarizer.SummaryService.get_summary',
        raise_auth
    )

    resp = auth_client.get('/summarizer/view/999', follow_redirects=True)
    assert resp.status_code == 200
    assert b'No permission' in resp.data


def test_delete_success(monkeypatch, auth_client):
    called = {'ok': False}

    def fake_delete(summary_id, user_id):
        called['ok'] = True

    monkeypatch.setattr(
        'app.routes.summarizer.SummaryService.delete_summary',
        fake_delete
    )

    resp = auth_client.post('/summarizer/delete/1', follow_redirects=True)
    assert resp.status_code == 200
    assert called['ok'] is True
    assert b'Summary deleted successfully' in resp.data


def test_delete_handles_errors(monkeypatch, auth_client):
    def raise_auth(summary_id, user_id):
        raise AuthorizationError('Denied')

    monkeypatch.setattr(
        'app.routes.summarizer.SummaryService.delete_summary',
        raise_auth
    )

    resp = auth_client.post('/summarizer/delete/1', follow_redirects=True)
    assert resp.status_code == 200
    assert b'Denied' in resp.data


def test_upload_no_file(auth_client):
    resp = auth_client.post('/summarizer/upload', data={}, follow_redirects=True)
    assert resp.status_code == 200
    assert b'No file selected' in resp.data


def test_upload_success_redirects(monkeypatch, auth_client):
    # Patch the create_summary_from_file to avoid filesystem or heavy processing
    def fake_create(user_id, file, title, use_ocr, upload_folder):
        return SimpleNamespace(id=42)

    monkeypatch.setattr(
        'app.routes.summarizer.SummaryService.create_summary_from_file',
        fake_create
    )

    data = {
        'title': 'My Title',
        'use_ocr': 'on',
        'file': (io.BytesIO(b'dummy'), 'doc.pdf')
    }

    resp = auth_client.post('/summarizer/upload', data=data, content_type='multipart/form-data', follow_redirects=False)
    # Should redirect to the view page for the created summary
    assert resp.status_code in (302, 303)
    assert '/summarizer/view/42' in resp.headers.get('Location', '')
