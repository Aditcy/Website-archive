import time

import httpx
from sqlalchemy import func, select

from ..config import cfg
from ..db import Ses
from ..models import Domain, URL, Crawl
from ..time import utcnow
from .feeds import find as feedfind
from .html import links
from .normalize import host, norm
from .robots import allowed as robots_allowed
from .robots import read as robots_read
from .sitemap import get as smget
from .sitemap import urls as smurls


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
            follow_redirects=True,
        )

        if response.status_code < 400:
            for sitemap_url in maps_from_robots(response.text):
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
                    continue

    except Exception:
        pass

    db.commit()


def maps_from_robots(txt):
    result = []

    for line in txt.splitlines():
        line = line.strip()

        if not line:
            continue

        if line.lower().startswith("sitemap:"):
            value = line.split(":", 1)[1].strip()

            if value:
                result.append(value)

    return result


def crawl_counts(db, did):
    total = (
        db.scalar(
            select(func.count(URL.id)).where(
                URL.domain_id == did
            )
        )
        or 0
    )

    done = (
        db.scalar(
            select(func.count(URL.id)).where(
                URL.domain_id == did,
                URL.checked_at.is_not(None),
            )
        )
        or 0
    )

    failed = (
        db.scalar(
            select(func.count(URL.id)).where(
                URL.domain_id == did,
                URL.status == "error",
            )
        )
        or 0
    )

    return total, done, failed


def run(did, rid):
    db = Ses()
    crawl = None

    processed_this_run = 0

    try:
        domain = db.get(Domain, did)
        crawl = db.get(Crawl, rid)

        if not domain:
            raise RuntimeError(
                f"domain {did} not found"
            )

        if not crawl:
            raise RuntimeError(
                f"crawl {rid} not found"
            )

        if not domain.active:
            raise RuntimeError(
                f"domain {did} is inactive"
            )

        # The Celery task must claim the crawl before calling run().
        #
        # If the crawl isn't already running, this is an old/stale
        # task and must NOT start crawling.
        if crawl.status != "running":
            return

        crawl.heartbeat = utcnow()
        db.commit()

        seed(db, did)

        robots = robots_read(domain.base_url)

        while processed_this_run < cfg.max_urls:

            # Allow a cancel operation to stop the crawl.
            db.refresh(crawl)

            if crawl.status != "running":
                return

            remaining = (
                cfg.max_urls - processed_this_run
            )

            rows = (
                db.execute(
                    select(URL)
                    .where(
                        URL.domain_id == did,
                        URL.checked_at.is_(None),
                    )
                    .order_by(URL.id)
                    .limit(
                        min(
                            cfg.batch,
                            remaining,
                        )
                    )
                )
                .scalars()
                .all()
            )

            if not rows:
                break

            for url_row in rows:

                if processed_this_run >= cfg.max_urls:
                    break

                db.refresh(crawl)

                if crawl.status != "running":
                    return

                crawl.heartbeat = utcnow()
                db.commit()

                if not robots_allowed(
                    robots,
                    url_row.norm,
                    cfg.user_agent,
                ):
                    now = utcnow()

                    url_row.status = "skipped"
                    url_row.crawled_at = now
                    url_row.checked_at = now

                    processed_this_run += 1

                    total, done, failed = crawl_counts(
                        db,
                        did,
                    )

                    crawl.total = total
                    crawl.done = done
                    crawl.failed = failed
                    crawl.heartbeat = utcnow()

                    db.commit()
                    continue

                try:
                    response = httpx.get(
                        url_row.norm,
                        headers={
                            "User-Agent": cfg.user_agent,
                        },
                        timeout=cfg.timeout,
                        follow_redirects=True,
                    )

                    url_row.http_status = response.status_code

                    url_row.content_type = response.headers.get(
                        "content-type",
                        "",
                    )[:120]

                    final_url = str(response.url)

                    url_row.redirect = (
                        final_url
                        if final_url != url_row.norm
                        else None
                    )

                    now = utcnow()

                    url_row.crawled_at = now
                    url_row.checked_at = now

                    if response.status_code < 400:
                        url_row.status = "ok"
                    else:
                        url_row.status = "error"

                    if "text/html" in url_row.content_type.lower():

                        for discovered in links(
                            response.text,
                            final_url,
                        ):
                            add(
                                db,
                                did,
                                discovered,
                                "html",
                                url_row.norm,
                            )

                        for feed_url in feedfind(
                            response.text,
                            final_url,
                        ):
                            add(
                                db,
                                did,
                                feed_url,
                                "feed",
                                url_row.norm,
                            )

                    processed_this_run += 1

                    total, done, failed = crawl_counts(
                        db,
                        did,
                    )

                    crawl.total = total
                    crawl.done = done
                    crawl.failed = failed
                    crawl.heartbeat = utcnow()

                    db.commit()

                    if cfg.delay > 0:
                        time.sleep(cfg.delay)

                except Exception as e:

                    now = utcnow()

                    url_row.crawled_at = now
                    url_row.checked_at = now
                    url_row.status = "error"

                    processed_this_run += 1

                    total, done, failed = crawl_counts(
                        db,
                        did,
                    )

                    crawl.total = total
                    crawl.done = done
                    crawl.failed = failed
                    crawl.error = str(e)[:1000]
                    crawl.heartbeat = utcnow()

                    db.commit()

        total, done, failed = crawl_counts(
            db,
            did,
        )

        crawl.total = total
        crawl.done = done
        crawl.failed = failed
        crawl.heartbeat = utcnow()

        crawl.status = "done"
        crawl.finished_at = utcnow()

        domain.last_scan = utcnow()

        db.commit()

        if cfg.auto_submit:
            from ..services.submission_service import make

            make(
                db,
                did,
                cfg.archive_service,
            )

    except Exception as e:

        try:
            if crawl:
                crawl.status = "failed"
                crawl.error = str(e)[:1000]
                crawl.finished_at = utcnow()
                crawl.heartbeat = utcnow()

                db.commit()

        except Exception:
            pass

        raise

    finally:
        db.close()
