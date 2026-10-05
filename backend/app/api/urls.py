from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..db import get
from ..models import URL
from ..schemas.url import UrlOut


r = APIRouter(prefix="/api/urls", tags=["urls"])


@r.get("")
def all(
    domain: int | None = None,
    q: str = "",
    status: str | None = None,
    page: int = 1,
    size: int = 50,
    db: Session = Depends(get),
):
    page = max(page, 1)
    size = min(max(size, 1), 200)

    query = select(URL)

    if domain is not None:
        query = query.where(URL.domain_id == domain)

    if status:
        query = query.where(URL.status == status)

    if q:
        query = query.where(
            or_(
                URL.norm.ilike(f"%{q}%"),
                URL.url.ilike(f"%{q}%"),
            )
        )

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
        UrlOut.model_validate(row).model_dump()
        for row in rows
    ]


@r.get("/{uid}", response_model=UrlOut)
def one(uid: int, db: Session = Depends(get)):
    row = db.get(URL, uid)

    if not row:
        raise HTTPException(404, "url not found")

    return row
