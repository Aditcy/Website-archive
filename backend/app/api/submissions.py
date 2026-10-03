from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get
from ..models import Submission
from ..services.submission_service import make

r = APIRouter(prefix="/api/submissions", tags=["submissions"])


@r.post("/queue/{did}")
def queue(
    did: int,
    service: str = "wayback",
    db: Session = Depends(get),
):
    return {
        "queued": make(db, did, service),
        "service": service,
    }


@r.get("")
def all(
    domain: int | None = None,
    status: str | None = None,
    service: str | None = None,
    db: Session = Depends(get),
):
    query = select(Submission)

    if domain:
        query = query.join(Submission.url).where(
            Submission.url.has(domain_id=domain)
        )

    if status:
        query = query.where(Submission.status == status)

    if service:
        query = query.where(Submission.service == service)

    rows = (
        db.execute(
            query.order_by(Submission.id.desc()).limit(200)
        )
        .scalars()
        .all()
    )

    return [
        {
            "id": s.id,
            "url": s.url.norm,
            "service": s.service,
            "status": s.status,
            "archive_url": s.archive_url,
            "error": s.error,
            "tries": s.attempts,
        }
        for s in rows
    ]
