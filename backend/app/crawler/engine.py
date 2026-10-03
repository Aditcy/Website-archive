import time
import httpx
from sqlalchemy import select, func

from ..time import utcnow
from ..config import cfg
from ..db import Ses
from ..models import Domain, URL, Crawl
from .normalize import norm, host
from .html import links
from .sitemap import get as smget, urls as smurls
from .robots import maps


def add(db, did, raw, src, srcu=None):
    u = norm(raw)
    if not u:
        return None

    d = db.get(Domain, did)
    if not d:
        return None

    base_host = host(d.base_url)
    url_host = host(u)

    if url_host != base_host and not url_host.endswith("." + base_host):
        return None

    existing = db.execute(
        select(URL).where(
            URL.domain_id == did,
            URL.norm == u,
        )
    ).scalar_one_or_none()

    if existing:
        return existing, False

    row = URL(
        domain_id=did,
        url=raw,
        norm=u,
        source=src,
    )

    db.add(row)
    db.flush()

    return row, True


def seed(db, did):
    d = db.get(Domain, did)
    if not d:
        return

    add(db, did, d.base_url, "root")

    robots_url = d.base_url.rstrip("/") + "/robots.txt"

    try:
        response = httpx.get(
            robots_url,
            headers={"User-Agent": cfg.user_agent},
            timeout=cfg.timeout,
        )

        for sitemap_url in maps(response.text):
            try:
                sitemap_data = smget(
                    sitemap_url,
                    {"User-Agent": cfg.user_agent},
                )

                for discovered_url in smurls(sitemap_data):
                    add(
                        db,
                        did,
                        discovered_url,
                        "sitemap",
                        sitemap_url,
                    )
            except Exception:
                pass

    except Exception:
        pass

    db.commit()


def run(did, rid):
    db = Ses()
    c = None

    try:
        d = db.get(Domain, did)
        c = db.get(Crawl, rid)

        if not d:
            raise RuntimeError(f"domain {did} not found")

        if not c:
            raise RuntimeError(f"crawl {rid} not found")

        c.status = "running"
        c.started_at = utcnow()
        c.heartbeat = utcnow()
        c.total = 0
        c.done = 0
        c.failed = 0
        c.error = None

        db.query(URL).filter(
            URL.domain_id == did
        ).update(
            {URL.checked_at: None},
            synchronize_session=False,
        )

        db.commit()

        seed(db, did)

        while True:
            rows = db.execute(
                select(URL)
                .where(
                    URL.domain_id == did,
                    URL.checked_at.is_(None),
                )
                .limit(cfg.batch)
            ).scalars().all()

            if not rows:
                break

            for u in rows:
                c.heartbeat = utcnow()

                try:
                    response = httpx.get(
                        u.norm,
                        headers={"User-Agent": cfg.user_agent},
                        timeout=cfg.timeout,
                        follow_redirects=True,
                    )

                    u.http_status = response.status_code
                    u.content_type = response.headers.get(
                        "content-type",
                        "",
                    )[:120]

                    final_url = str(response.url)

                    u.redirect = (
                        final_url
                        if final_url != u.norm
                        else None
                    )

                    now = utcnow()
                    u.crawled_at = now
                    u.checked_at = now

                    if response.status_code < 400:
                        u.status = "ok"
                        c.done += 1
                    else:
                        u.status = "error"
                        c.failed += 1

                    if "text/html" in u.content_type:
                        for discovered in links(
                            response.text,
                            final_url,
                        ):
                            add(
                                db,
                                did,
                                discovered,
                                "html",
                                u.norm,
                            )

                    c.total = db.scalar(
                        select(func.count(URL.id)).where(
                            URL.domain_id == did
                        )
                    ) or 0

                    db.commit()

                    time.sleep(cfg.delay)

                except Exception as e:
                    now = utcnow()

                    u.crawled_at = now
                    u.checked_at = now
                    u.status = "error"

                    c.failed += 1
                    c.error = str(e)[:1000]
                    c.heartbeat = utcnow()

                    c.total = db.scalar(
                        select(func.count(URL.id)).where(
                            URL.domain_id == did
                        )
                    ) or 0

                    db.commit()

        c.total = db.scalar(
            select(func.count(URL.id)).where(
                URL.domain_id == did
            )
        ) or 0

        c.done = db.scalar(
            select(func.count(URL.id)).where(
                URL.domain_id == did,
                URL.domain_id == did,
                URL.checked_at.is_not(None),
            )
        ) or 0

        c.failed = db.scalar(
            select(func.count(URL.id)).where(
                URL.domain_id == did,
                URL.status == "error",
            )
        ) or 0

        c.status = "done"
        c.finished_at = utcnow()
        c.heartbeat = utcnow()

        d.last_scan = utcnow()

        db.commit()

        if cfg.auto_submit:
            from ..services.submission_service import make
            make(db, did, cfg.archive_service)

    except Exception as e:
        try:
            if c:
                c.status = "failed"
                c.error = str(e)[:1000]
                c.finished_at = utcnow()
                c.heartbeat = utcnow()
                db.commit()
        except Exception:
            pass

        raise

    # Do not close db here.
    # The caller owns the session. Tests intentionally inject their
    # session through engine.Ses, and the worker's caller owns cleanup.
