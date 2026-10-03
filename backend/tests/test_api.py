from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get
from app.main import app
from app.models import Domain, URL, Submission, Crawl


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    Base.metadata.create_all(engine)

    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture
def client(db):
    # Prevent the FastAPI startup hook from initializing the real
    # configured PostgreSQL database during isolated API tests.
    with patch("app.main.init"):
        app.dependency_overrides[get] = lambda: db

        with TestClient(app) as client:
            yield client

        app.dependency_overrides.clear()


def test_create_domain(client):
    response = client.post(
        "/api/domains",
        json={"url": "https://Example.COM/"},
    )

    assert response.status_code == 200

    data = response.json()

    assert data["name"] == "example.com"
    assert data["base_url"] == "https://Example.COM"


def test_duplicate_domain_returns_existing_domain(client, db):
    first = client.post(
        "/api/domains",
        json={"url": "https://example.com/"},
    )

    second = client.post(
        "/api/domains",
        json={"url": "https://example.com"},
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["id"] == second.json()["id"]

    assert db.query(Domain).count() == 1


def test_scan_nonexistent_domain_returns_404(client):
    response = client.post("/api/domains/99999/scan")

    assert response.status_code == 404
    assert response.json()["detail"] == "domain not found"


def test_crawl_endpoint_returns_status(client, db):
    domain = Domain(
        name="example.com",
        base_url="https://example.com",
    )
    db.add(domain)
    db.commit()
    db.refresh(domain)

    crawl = Crawl(
        domain_id=domain.id,
        status="running",
        total=4,
        done=2,
        failed=1,
        error="test error",
    )
    db.add(crawl)
    db.commit()
    db.refresh(crawl)

    response = client.get(f"/api/crawls/{crawl.id}")

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == crawl.id
    assert data["domain_id"] == domain.id
    assert data["status"] == "running"
    assert data["total"] == 4
    assert data["done"] == 2
    assert data["failed"] == 1
    assert data["error"] == "test error"


def test_missing_crawl_returns_404(client):
    response = client.get("/api/crawls/99999")

    assert response.status_code == 404
    assert response.json()["detail"] == "crawl not found"


def test_urls_api_filters_and_paginates(client, db):
    domain = Domain(
        name="example.com",
        base_url="https://example.com",
    )
    db.add(domain)
    db.commit()
    db.refresh(domain)

    for path in ["/one", "/two", "/three"]:
        db.add(
            URL(
                domain_id=domain.id,
                url=f"https://example.com{path}",
                norm=f"https://example.com{path}",
                status="ok",
                http_status=200,
                source="test",
            )
        )

    db.commit()

    response = client.get(
        "/api/urls",
        params={
            "domain": domain.id,
            "q": "two",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["norm"] == "https://example.com/two"


def test_submissions_api_filters(client, db):
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

    db.add_all(
        [
            Submission(
                url_id=url.id,
                service="wayback",
                status="success",
                attempts=1,
                archive_url="https://web.archive.org/example",
            ),
            Submission(
                url_id=url.id,
                service="archive_today",
                status="failed",
                attempts=3,
                error="test failure",
            ),
        ]
    )
    db.commit()

    response = client.get(
        "/api/submissions",
        params={
            "service": "wayback",
            "status": "success",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["service"] == "wayback"
    assert data[0]["status"] == "success"
    assert data[0]["tries"] == 1


def test_dashboard_counters(client, db):
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

    db.add_all(
        [
            Submission(
                url_id=url.id,
                service="wayback",
                status="success",
            ),
            Submission(
                url_id=url.id,
                service="archive_today",
                status="failed",
            ),
            Submission(
                url_id=url.id,
                service="test",
                status="manual",
            ),
            Submission(
                url_id=url.id,
                service="other",
                status="queued",
            ),
        ]
    )
    db.commit()

    response = client.get("/api/dashboard")

    assert response.status_code == 200

    data = response.json()

    assert data["domains"] == 1
    assert data["urls"] == 1
    assert data["submitted"] == 1
    assert data["success"] == 1
    assert data["failed"] == 1
    assert data["manual"] == 1
    assert data["pending"] == 1
    assert data["queued"] == 1


def test_queue_endpoint_uses_service_parameter(client, db):
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

    with patch("app.services.submission_service.sub.delay"):
        response = client.post(
            f"/api/submissions/queue/{domain.id}",
            params={"service": "wayback"},
        )

    assert response.status_code == 200
    assert response.json()["service"] == "wayback"
    assert response.json()["queued"] == 1


def test_unknown_archive_service_is_reported_by_worker(db):
    from app.workers import tasks

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
        service="does_not_exist",
        status="queued",
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)

    sid = submission.id

    with patch.object(tasks, "Ses", return_value=db):
        tasks.sub.run(sid)

    db.refresh(submission)

    assert submission.status == "failed"
    assert "Unknown archive service" in submission.error
