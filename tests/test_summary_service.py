import io
from werkzeug.datastructures import FileStorage
from types import SimpleNamespace

import pytest

from app.services.summary_service import SummaryService
from app.models import Summary, User
from app.exceptions import ValidationError, NotFoundError, AuthorizationError


def make_filestorage(data=b'data', filename='doc.pdf'):
    return FileStorage(stream=io.BytesIO(data), filename=filename, content_type='application/pdf')


def test_create_summary_success(db_session, test_user, monkeypatch, tmp_path):
    # Patch document processor helpers
    monkeypatch.setattr('app.services.summary_service.get_allowed_extensions', lambda: {'pdf', 'docx'})
    monkeypatch.setattr('app.services.summary_service.get_file_type', lambda fname: 'pdf')
    monkeypatch.setattr('app.services.summary_service.extract_text', lambda path, ftype: (True, 'This is sufficient extracted text for summary.'))
    monkeypatch.setattr('app.services.summary_service.generate_summary', lambda text: 'Generated summary')

    upload_folder = str(tmp_path)
    file = make_filestorage(b'pdfbytes', 'document.pdf')

    new_summary = SummaryService.create_summary_from_file(
        user_id=test_user.id,
        file=file,
        title='My Doc',
        use_ocr=False,
        upload_folder=upload_folder
    )

    assert isinstance(new_summary, Summary)
    assert new_summary.user_id == test_user.id
    assert new_summary.summary_text == 'Generated summary'
    # Ensure temporary file cleaned up
    assert not any(tmp_path.iterdir())


def test_create_summary_user_not_found(db_session, monkeypatch, tmp_path):
    # No users in DB besides session-created ones; use non-existent id
    monkeypatch.setattr('app.services.summary_service.get_allowed_extensions', lambda: {'pdf'})
    file = make_filestorage(b'x', 'doc.pdf')

    with pytest.raises(NotFoundError):
        SummaryService.create_summary_from_file(
            user_id=999999,
            file=file,
            title='T',
            use_ocr=False,
            upload_folder=str(tmp_path)
        )


def test_create_summary_invalid_extension(db_session, test_user, monkeypatch, tmp_path):
    monkeypatch.setattr('app.services.summary_service.get_allowed_extensions', lambda: {'docx'})
    file = make_filestorage(b'x', 'bad.pdf')

    with pytest.raises(ValidationError):
        SummaryService.create_summary_from_file(
            user_id=test_user.id,
            file=file,
            title='T',
            use_ocr=False,
            upload_folder=str(tmp_path)
        )


def test_create_summary_no_file(db_session, test_user, tmp_path):
    with pytest.raises(ValidationError):
        SummaryService.create_summary_from_file(
            user_id=test_user.id,
            file=None,
            title='T',
            use_ocr=False,
            upload_folder=str(tmp_path)
        )


def test_create_summary_short_extracted_text(db_session, test_user, monkeypatch, tmp_path):
    monkeypatch.setattr('app.services.summary_service.get_allowed_extensions', lambda: {'pdf'})
    monkeypatch.setattr('app.services.summary_service.get_file_type', lambda fname: 'pdf')
    monkeypatch.setattr('app.services.summary_service.extract_text', lambda path, ftype: (True, 'short'))

    file = make_filestorage(b'x', 'doc.pdf')

    with pytest.raises(ValidationError):
        SummaryService.create_summary_from_file(
            user_id=test_user.id,
            file=file,
            title='T',
            use_ocr=False,
            upload_folder=str(tmp_path)
        )


def test_get_summary_not_found(db_session, test_user):
    with pytest.raises(NotFoundError):
        SummaryService.get_summary(9999, test_user.id)


def test_get_summary_authorization(db_session, test_user, test_user_2):
    # Create a summary for user2
    s = Summary(title='A', original_filename='f', file_type='pdf', user_id=test_user_2.id, extracted_text='x', summary_text='y')
    db_session.session.add(s)
    db_session.session.commit()

    with pytest.raises(AuthorizationError):
        SummaryService.get_summary(s.id, test_user.id)


def test_delete_summary_success(db_session, test_user):
    s = Summary(title='Del', original_filename='f', file_type='pdf', user_id=test_user.id, extracted_text='x', summary_text='y')
    db_session.session.add(s)
    db_session.session.commit()

    SummaryService.delete_summary(s.id, test_user.id)
    assert db_session.session.get(Summary, s.id) is None


def test_delete_summary_not_found(db_session, test_user):
    with pytest.raises(NotFoundError):
        SummaryService.delete_summary(99999, test_user.id)


def test_delete_summary_authorization(db_session, test_user, test_user_2):
    s = Summary(title='Del2', original_filename='f', file_type='pdf', user_id=test_user_2.id, extracted_text='x', summary_text='y')
    db_session.session.add(s)
    db_session.session.commit()

    with pytest.raises(AuthorizationError):
        SummaryService.delete_summary(s.id, test_user.id)
