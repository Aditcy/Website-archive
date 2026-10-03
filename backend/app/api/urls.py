from fastapi import APIRouter, Depends
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..db import get
from ..models import URL

r = APIRouter(prefix="/api/urls", tags=["urls"])


@r.get("")
def all(
    domain: int | None = None,
    q: str = "",
    page: int = 1,
    size: int = 50,
    db: Session = Depends(get),
):
    query = select(URL)

    if domain:
        query = query.where(URL.domain_id == domain)

    if q:
        query = query.where(
            or_(
                URL.norm.ilike(f"%{q}%"),
                URL.url.ilike(f"%{q}%"),
            )
        )

    page = max(page, 1)
    size = min(max(size, 1), 200)

    rows = (
        db.execute(
            query.order_by(URL.id.desc())
            .offset((page - 1) * size)
            .limit(size)
        )
        .scalars()
        .all()
    )

    return [
        {
            "id": u.id,
            "domain_id": u.domain_id,
            "url": u.url,
            "norm": u.norm,
            "status": u.status,
            "http_status": u.http_status,
            "content_type": u.content_type,
            "redirect": u.redirect,
            "source": u.source,
            "discovered_at": u.discovered_at,
            "crawled_at": u.crawled_at,
            "checked_at": u.checked_at,
            "queued": u.queued,
        }
        for u in rows
    ]
