from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get
from ..models import Crawl


r = APIRouter(prefix="/api/crawls", tags=["crawls"])


def serialize(crawl: Crawl):
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

    total = db.scalar(
        select(func.count())
        .select_from(query.subquery())
    ) or 0

    rows = (
        db.execute(
            query.order_by(Crawl.id.desc())
            .offset((page - 1) * size)
            .limit(size)
        )
        .scalars()
        .all()
    )

    return {
        "items": [serialize(crawl) for crawl in rows],
        "page": page,
        "size": size,
        "total": total,
    }


@r.get("/{cid}")
def one(cid: int, db: Session = Depends(get)):
    crawl = db.get(Crawl, cid)

    if not crawl:
        raise HTTPException(404, "crawl not found")

    return serialize(crawl)
