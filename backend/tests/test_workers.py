from unittest.mock import Mock, patch
from celery.exceptions import Retry

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.models import Domain, URL, Submission
from app.workers import tasks


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def make_submission(db, service="wayback", status="queued"):
    domain = Domain(
        name="example.com",
        base_url="https://example.com",
    )
    db.add(domain)
    db.commit()
    db.refresh(domain)

    url = URL(
        domain_id=domain.id,
        url="https://example.com/",
        norm="https://example.com/",
        status="ok",
        http_status=200,
    )
    db.add(url)
    db.commit()
    db.refresh(url)

    submission = Submission(
        url_id=url.id,
        service=service,
        status=status,
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)

    return submission


def test_submission_worker_success(db):
    submission = make_submission(db)

    provider = Mock()
    provider.submit.return_value = Mock(
        ok=True,
        url="https://web.archive.org/web/20260101/https://example.com/",
        aid="abc123",
        err=None,
    )

    with patch.object(tasks, "Ses", return_value=db), \
         patch.object(tasks, "get", return_value=provider):

        tasks.sub.run(submission.id)

    db.refresh(submission)

    assert submission.status == "success"
    assert submission.archive_url == (
        "https://web.archive.org/web/20260101/https://example.com/"
    )
    assert submission.submitted_at is not None
    assert submission.error is None
    assert submission.attempts == 1

    provider.submit.assert_called_once_with(
        "https://example.com/"
    )


def test_submission_worker_manual_required(db):
    submission = make_submission(db, service="archive_today")

    provider = Mock()
    provider.submit.return_value = Mock(
        ok=False,
        url="https://archive.today/?run=1&url=https%3A%2F%2Fexample.com%2F",
        aid=None,
        err="manual_required",
    )

    with patch.object(tasks, "Ses", return_value=db), \
         patch.object(tasks, "get", return_value=provider):

        tasks.sub.run(submission.id)

    db.refresh(submission)

    assert submission.status == "manual"
    assert submission.archive_url.startswith("https://archive.today/")
    assert submission.error == "manual_required"
    assert submission.submitted_at is not None
    assert submission.attempts == 1


def test_submission_worker_auth_failure(db):
    submission = make_submission(db)

    provider = Mock()
    provider.submit.return_value = Mock(
        ok=False,
        url=None,
        aid=None,
        err="auth_required: credentials rejected",
    )

    with patch.object(tasks, "Ses", return_value=db), \
         patch.object(tasks, "get", return_value=provider):

        tasks.sub.run(submission.id)

    db.refresh(submission)

    assert submission.status == "failed"
    assert submission.error == "auth_required: credentials rejected"
    assert submission.attempts == 1


def test_submission_worker_does_nothing_for_success(db):
    submission = make_submission(db, status="success")
    submission.archive_url = "https://web.archive.org/example"
    db.commit()

    provider = Mock()

    with patch.object(tasks, "Ses", return_value=db), \
         patch.object(tasks, "get", return_value=provider):

        tasks.sub.run(submission.id)

    db.refresh(submission)

    assert submission.status == "success"
    assert submission.attempts == 0
    provider.submit.assert_not_called()


def test_submission_worker_final_failure(db):
    submission = make_submission(db)

    provider = Mock()
    provider.submit.return_value = Mock(
        ok=False,
        url=None,
        aid=None,
        err="HTTP 500: capture failed",
    )

    with patch.object(tasks, "Ses", return_value=db), \
         patch.object(tasks, "get", return_value=provider), \
         patch.object(tasks.cfg, "retries", 1):

        tasks.sub.run(submission.id)

    db.refresh(submission)

    assert submission.status == "failed"
    assert submission.error == "HTTP 500: capture failed"
    assert submission.attempts == 1


def test_submission_worker_retries_temporary_failure(db):
    submission = make_submission(db)

    provider = Mock()
    provider.submit.return_value = Mock(
        ok=False,
        url=None,
        aid=None,
        err="HTTP 503: temporary failure",
    )

    with patch.object(tasks, "Ses", return_value=db), \
         patch.object(tasks, "get", return_value=provider), \
         patch.object(tasks.cfg, "retries", 3), \
         patch.object(
             tasks.sub,
             "retry",
             side_effect=tasks.Retry(),
         ) as retry:

        with pytest.raises(tasks.Retry):
            tasks.sub.run(submission.id)

    db.refresh(submission)

    assert submission.status == "retry"
    assert submission.attempts == 1
    assert submission.error == "HTTP 503: temporary failure"
    retry.assert_called_once()


def test_submission_worker_retries_then_succeeds(db):
    submission = make_submission(db)

    provider = Mock()
    provider.submit.side_effect = [
        Mock(
            ok=False,
            url=None,
            aid=None,
            err="HTTP 503: temporary failure",
        ),
        Mock(
            ok=True,
            url="https://web.archive.org/web/20260101/https://example.com/",
            aid="abc123",
            err=None,
        ),
    ]

    with patch.object(tasks, "Ses", return_value=db), \
         patch.object(tasks, "get", return_value=provider), \
         patch.object(tasks.cfg, "retries", 3), \
         patch.object(
             tasks.sub,
             "retry",
             side_effect=tasks.Retry(),
         ):

        with pytest.raises(tasks.Retry):
            tasks.sub.run(submission.id)

    db.refresh(submission)

    assert submission.status == "retry"
    assert submission.attempts == 1

    with patch.object(tasks, "Ses", return_value=db), \
         patch.object(tasks, "get", return_value=provider):

        tasks.sub.run(submission.id)

    db.refresh(submission)

    assert submission.status == "success"
    assert submission.attempts == 2
    assert submission.archive_url == (
        "https://web.archive.org/web/20260101/https://example.com/"
    )
    assert submission.error is None
    assert provider.submit.call_count == 2


def test_submission_worker_exception_marks_failed(db):
    submission = make_submission(db)

    provider = Mock()
    provider.submit.side_effect = RuntimeError("provider crashed")

    with patch.object(tasks, "Ses", return_value=db), \
         patch.object(tasks, "get", return_value=provider):

        with pytest.raises(RuntimeError, match="provider crashed"):
            tasks.sub.run(submission.id)

    db.refresh(submission)

    assert submission.status == "failed"
    assert submission.attempts == 1
    assert submission.error == "provider crashed"


def test_submission_worker_does_not_retry_daily_capture_limit(db):
    submission = make_submission(db)

    provider = Mock()
    provider.submit.return_value = Mock(
        ok=False,
        url=None,
        aid=None,
        err="This URL has been already captured 5 times today.",
    )

    with patch.object(tasks, "Ses", return_value=db), \
         patch.object(tasks, "get", return_value=provider), \
         patch.object(tasks.cfg, "retries", 3), \
         patch.object(tasks.sub, "retry") as retry:

        tasks.sub.run(submission.id)

        retry.assert_not_called()

    db.refresh(submission)

    assert submission.status == "failed"
    assert submission.error == (
        "This URL has been already captured 5 times today."
    )
    assert submission.attempts == 1
