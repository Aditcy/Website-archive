import pytest
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.models import Domain, URL, Submission, Crawl
from app.services import crawl_service, submission_service, incremental_service


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


def test_crawl_start_creates_crawl_and_queues_task(db):
    domain = Domain(
        name="example.com",
        base_url="https://example.com",
    )
    db.add(domain)
    db.commit()
    db.refresh(domain)

    with patch.object(crawl_service.crawl, "delay") as delay:
        result = crawl_service.start(db, domain.id)

        assert result.id is not None
        assert result.domain_id == domain.id
        assert result.status == "queued"

        delay.assert_called_once_with(domain.id, result.id)


def test_submission_make_queues_only_ok_urls(db):
    domain = Domain(
        name="example.com",
        base_url="https://example.com",
    )
    db.add(domain)
    db.commit()
    db.refresh(domain)

    good = URL(
        domain_id=domain.id,
        url="https://example.com/",
        norm="https://example.com/",
        status="ok",
        http_status=200,
    )

    bad = URL(
        domain_id=domain.id,
        url="https://example.com/missing",
        norm="https://example.com/missing",
        status="error",
        http_status=404,
    )

    db.add_all([good, bad])
    db.commit()

    with patch.object(submission_service.sub, "delay") as delay:
        count = submission_service.make(db, domain.id, "wayback")

        assert count == 1

        submission = (
            db.query(Submission)
            .filter_by(url_id=good.id, service="wayback")
            .one()
        )

        assert submission.status == "queued"
        delay.assert_called_once_with(submission.id)

        assert (
            db.query(Submission)
            .filter_by(url_id=bad.id)
            .count()
            == 0
        )


def test_submission_make_does_not_duplicate_queued_submission(db):
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

    existing = Submission(
        url_id=url.id,
        service="wayback",
        status="queued",
    )
    db.add(existing)
    db.commit()

    with patch.object(submission_service.sub, "delay") as delay:
        count = submission_service.make(db, domain.id, "wayback")

        assert count == 0
        delay.assert_called_once_with(existing.id)

        assert (
            db.query(Submission)
            .filter_by(url_id=url.id, service="wayback")
            .count()
            == 1
        )


def test_submission_make_does_not_duplicate_successful_submission(db):
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

    successful = Submission(
        url_id=url.id,
        service="wayback",
        status="success",
        archive_url="https://web.archive.org/example",
    )
    db.add(successful)
    db.commit()

    with patch.object(submission_service.sub, "delay") as delay:
        count = submission_service.make(db, domain.id, "wayback")

        assert count == 0
        delay.assert_not_called()

        assert (
            db.query(Submission)
            .filter_by(url_id=url.id, service="wayback")
            .count()
            == 1
        )


def test_incremental_returns_urls_without_successful_submission(db):
    domain = Domain(
        name="example.com",
        base_url="https://example.com",
    )
    db.add(domain)
    db.commit()
    db.refresh(domain)

    pending = URL(
        domain_id=domain.id,
        url="https://example.com/pending",
        norm="https://example.com/pending",
        status="ok",
        http_status=200,
    )

    archived = URL(
        domain_id=domain.id,
        url="https://example.com/archived",
        norm="https://example.com/archived",
        status="ok",
        http_status=200,
    )

    db.add_all([pending, archived])
    db.commit()
    db.refresh(archived)

    db.add(
        Submission(
            url_id=archived.id,
            service="wayback",
            status="success",
        )
    )
    db.commit()

    result = incremental_service.new(db, domain.id)

    ids = {u.id for u in result}

    assert pending.id in ids
    assert archived.id not in ids
