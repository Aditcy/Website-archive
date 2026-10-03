import pytest
from unittest.mock import patch, Mock

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.models import Domain, URL, Crawl
from app.crawler import engine


@pytest.fixture
def db():
    db_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(db_engine)

    Session = sessionmaker(bind=db_engine)
    session = Session()

    try:
        yield session
    finally:
        session.close()
        db_engine.dispose()


def make_domain(db, url="https://example.com"):
    domain = Domain(
        name="example.com",
        base_url=url,
    )
    db.add(domain)
    db.commit()
    db.refresh(domain)
    return domain


def run_with_db(db, did, rid):
    with patch.object(engine, "Ses", return_value=db):
        return engine.run(did, rid)


def test_add_normalizes_and_deduplicates(db):
    domain = make_domain(db)

    first, created = engine.add(
        db,
        domain.id,
        "https://EXAMPLE.com/test",
        "html",
    )

    second, created_again = engine.add(
        db,
        domain.id,
        "https://example.com/test",
        "html",
    )

    assert created is True
    assert created_again is False
    assert first.id == second.id
    assert db.query(URL).count() == 1


def test_add_rejects_external_host(db):
    domain = make_domain(db)

    result = engine.add(
        db,
        domain.id,
        "https://other.example.net/page",
        "html",
    )

    assert result is None
    assert db.query(URL).count() == 0


def test_add_accepts_subdomain(db):
    domain = make_domain(db)

    row, created = engine.add(
        db,
        domain.id,
        "https://www.example.com/page",
        "html",
    )

    assert created is True
    assert row.norm == "https://www.example.com/page"


def test_run_records_redirect(db):
    domain = make_domain(db)

    row, _ = engine.add(
        db,
        domain.id,
        "https://example.com/old",
        "root",
    )
    db.commit()

    crawl = Crawl(
        domain_id=domain.id,
        status="queued",
    )
    db.add(crawl)
    db.commit()
    db.refresh(crawl)

    response = Mock()
    response.status_code = 200
    response.url = "https://example.com/new"
    response.headers = {
        "content-type": "text/html; charset=utf-8"
    }
    response.text = "<html><body>Hello</body></html>"

    with patch.object(engine.httpx, "get", return_value=response):
        with patch.object(engine, "seed"):
            with patch.object(engine.time, "sleep"):
                run_with_db(db, domain.id, crawl.id)

    db.refresh(row)
    db.refresh(crawl)

    assert row.status == "ok"
    assert row.http_status == 200
    assert row.redirect == "https://example.com/new"
    assert row.checked_at is not None
    assert crawl.status == "done"


def test_run_records_http_error(db):
    domain = make_domain(db)

    row, _ = engine.add(
        db,
        domain.id,
        "https://example.com/missing",
        "root",
    )
    db.commit()

    crawl = Crawl(
        domain_id=domain.id,
        status="queued",
    )
    db.add(crawl)
    db.commit()
    db.refresh(crawl)

    response = Mock()
    response.status_code = 404
    response.url = "https://example.com/missing"
    response.headers = {
        "content-type": "text/html"
    }
    response.text = "not found"

    with patch.object(engine.httpx, "get", return_value=response):
        with patch.object(engine, "seed"):
            with patch.object(engine.time, "sleep"):
                run_with_db(db, domain.id, crawl.id)

    db.refresh(row)
    db.refresh(crawl)

    assert row.status == "error"
    assert row.http_status == 404
    assert crawl.status == "done"
    assert crawl.done == 1


def test_run_discovers_html_links(db):
    domain = make_domain(db)

    row, _ = engine.add(
        db,
        domain.id,
        "https://example.com/",
        "root",
    )
    db.commit()

    crawl = Crawl(
        domain_id=domain.id,
        status="queued",
    )
    db.add(crawl)
    db.commit()
    db.refresh(crawl)

    response = Mock()
    response.status_code = 200
    response.url = "https://example.com/"
    response.headers = {
        "content-type": "text/html"
    }
    response.text = """
    <html>
      <a href="/about">About</a>
      <a href="https://example.com/contact">Contact</a>
      <a href="https://other.example.net/">External</a>
    </html>
    """

    with patch.object(engine.httpx, "get", return_value=response):
        with patch.object(engine, "seed"):
            with patch.object(engine.time, "sleep"):
                run_with_db(db, domain.id, crawl.id)

    urls = {
        u.norm
        for u in db.query(URL)
        .filter(URL.domain_id == domain.id)
        .all()
    }

    assert "https://example.com/about" in urls
    assert "https://example.com/contact" in urls
    assert "https://other.example.net/" not in urls


def test_run_marks_crawl_failed_on_unexpected_error(db):
    domain = make_domain(db)

    crawl = Crawl(
        domain_id=domain.id,
        status="queued",
    )
    db.add(crawl)
    db.commit()
    db.refresh(crawl)

    with patch.object(engine, "seed", side_effect=RuntimeError("boom")):
        with pytest.raises(RuntimeError, match="boom"):
            run_with_db(db, domain.id, crawl.id)

    db.refresh(crawl)

    assert crawl.status == "failed"
    assert "boom" in crawl.error


def test_run_updates_crawl_counters(db):
    domain = make_domain(db)

    for path in ["/one", "/two"]:
        engine.add(
            db,
            domain.id,
            f"https://example.com{path}",
            "root",
        )

    db.commit()

    crawl = Crawl(
        domain_id=domain.id,
        status="queued",
    )
    db.add(crawl)
    db.commit()
    db.refresh(crawl)

    def fake_get(url, **kwargs):
        response = Mock()
        response.status_code = 200
        response.url = url
        response.headers = {"content-type": "text/plain"}
        response.text = "ok"
        return response

    with patch.object(engine.httpx, "get", side_effect=fake_get):
        with patch.object(engine, "seed"):
            with patch.object(engine.time, "sleep"):
                run_with_db(db, domain.id, crawl.id)

    db.refresh(crawl)

    assert crawl.status == "done"
    assert crawl.total == 2
    assert crawl.done == 2
    assert crawl.failed == 0
