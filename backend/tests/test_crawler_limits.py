from unittest.mock import Mock, patch

from app.crawler import engine
from app.models import URL, Crawl, Domain


def make_domain(db, url="https://example.com"):
    domain = Domain(
        name="example.com",
        base_url=url,
    )
    db.add(domain)
    db.commit()
    db.refresh(domain)
    return domain


def test_run_respects_max_urls(db, monkeypatch):
    domain = make_domain(db)

    crawl = Crawl(
        domain_id=domain.id,
        status="queued",
    )
    db.add(crawl)
    db.commit()
    db.refresh(crawl)

    monkeypatch.setattr(engine.cfg, "max_urls", 2)
    monkeypatch.setattr(engine.cfg, "delay", 0)

    response = Mock()
    response.status_code = 200
    response.url = "https://example.com/"
    response.headers = {
        "content-type": "text/html; charset=utf-8"
    }
    response.text = """
        <html>
            <body>
                <a href="/page1">Page 1</a>
                <a href="/page2">Page 2</a>
                <a href="/page3">Page 3</a>
            </body>
        </html>
    """

    with patch.object(engine, "Ses", return_value=db):
        with patch.object(
            engine.httpx,
            "get",
            return_value=response,
        ):
            with patch.object(
                engine,
                "robots_read",
                return_value=None,
            ):
                with patch.object(engine, "seed"):
                    with patch.object(engine.time, "sleep"):
                        engine.run(domain.id, crawl.id)

    db.refresh(crawl)

    assert crawl.status == "done"
    assert db.query(URL).filter(
        URL.domain_id == domain.id
    ).count() <= 2
