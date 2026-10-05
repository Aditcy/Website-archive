import httpx

from app.crawler import engine


def test_run_handles_timeout(monkeypatch, db):
    domain = engine.Domain(
        name="example.com",
        base_url="https://example.com/",
    )
    db.add(domain)
    db.commit()
    db.refresh(domain)

    crawl = engine.Crawl(
        domain_id=domain.id,
        status="queued",
    )
    db.add(crawl)
    db.commit()
    db.refresh(crawl)

    def timeout(*args, **kwargs):
        raise httpx.TimeoutException("request timed out")

    monkeypatch.setattr(engine.httpx, "get", timeout)
    monkeypatch.setattr(engine, "robots_read", lambda base: None)
    monkeypatch.setattr(engine.cfg, "delay", 0)

    with monkeypatch.context() as m:
        m.setattr(engine, "Ses", lambda: db)

        engine.run(domain.id, crawl.id)

    db.refresh(crawl)

    assert crawl.status == "done"
    assert crawl.failed >= 1
    assert "timed out" in crawl.error


def test_run_handles_connection_error(monkeypatch, db):
    domain = engine.Domain(
        name="example.com",
        base_url="https://example.com/",
    )
    db.add(domain)
    db.commit()
    db.refresh(domain)

    crawl = engine.Crawl(
        domain_id=domain.id,
        status="queued",
    )
    db.add(crawl)
    db.commit()
    db.refresh(crawl)

    def connection_error(*args, **kwargs):
        raise httpx.ConnectError("DNS failure")

    monkeypatch.setattr(engine.httpx, "get", connection_error)
    monkeypatch.setattr(engine, "robots_read", lambda base: None)
    monkeypatch.setattr(engine.cfg, "delay", 0)

    with monkeypatch.context() as m:
        m.setattr(engine, "Ses", lambda: db)

        engine.run(domain.id, crawl.id)

    db.refresh(crawl)

    assert crawl.status == "done"
    assert crawl.failed >= 1
    assert "DNS failure" in crawl.error
