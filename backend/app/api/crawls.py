from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get
from ..models import Crawl


r = APIRouter(prefix="/api/crawls", tags=["crawls"])


@r.get("")
def all(
    domain: int | None = None,
    status: str | None = None,
    page: int = 1,
    size: int = 50,
    db: Session = Depends(get),
):
    page = max(page, 1)
    size = min(max(size, 1), 200)

    query = select(Crawl)

    if domain is not None:
        query = query.where(Crawl.domain_id == domain)

    if status:
        query = query.where(Crawl.status == status)

    rows = (
        db.execute(
            query.order_by(Crawl.id.desc())
            .offset((page - 1) * size)
            .limit(size)
        )
        .scalars()
        .all()
    )

    return [
        {
            "id": c.id,
            "domain_id": c.domain_id,
            "status": c.status,
            "total": c.total,
            "done": c.done,
            "failed": c.failed,
            "error": c.error,
            "started_at": c.started_at,
            "finished_at": c.finished_at,
            "heartbeat": c.heartbeat,
        }
        for c in rows
    ]


@r.get("/{cid}")
def one(cid: int, db: Session = Depends(get)):
    crawl = db.get(Crawl, cid)

    if not crawl:
        raise HTTPException(404, "crawl not found")

    return {
        "id": crawl.id,
        "domain_id": crawl.domain_id,
        "status": crawl.status,
        "total": crawl.total,
        "done": crawl.done,
        "failed": crawl.failed,
        "error": crawl.error,
        "started_at": crawl.started_at,
        "finished_at": crawl.finished_at,
        "heartbeat": crawl.heartbeat,
    }
