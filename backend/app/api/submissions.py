from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get
from ..models import Submission
from ..services.submission_service import make


r = APIRouter(
    prefix="/api/submissions",
    tags=["submissions"],
)


@r.post("/queue/{did}")
def queue(
    did: int,
    service: str = "wayback",
    db: Session = Depends(get),
):
    service = service.strip().lower()

    if service not in {"wayback", "archive_today"}:
        raise HTTPException(
            422,
            "unsupported archive service",
        )

    count = make(db, did, service)

    return {
        "queued": count,
        "service": service,
    }


@r.get("")
def all(
    domain: int | None = None,
    status: str | None = None,
    service: str | None = None,
    page: int = 1,
    size: int = 50,
    db: Session = Depends(get),
):
    page = max(page, 1)
    size = min(max(size, 1), 200)

    query = select(Submission)

    if domain is not None:
        query = query.join(
            Submission.url
        ).where(
            Submission.url.has(domain_id=domain)
        )

    if status:
        query = query.where(
            Submission.status == status
        )

    if service:
        query = query.where(
            Submission.service == service
        )

    rows = (
        db.execute(
            query.order_by(Submission.id.desc())
            .offset((page - 1) * size)
            .limit(size)
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


@r.get("/{sid}")
def one(sid: int, db: Session = Depends(get)):
    submission = db.get(Submission, sid)

    if not submission:
        raise HTTPException(
            404,
            "submission not found",
        )

    return {
        "id": submission.id,
        "url_id": submission.url_id,
        "url": submission.url.norm,
        "service": submission.service,
        "status": submission.status,
        "archive_url": submission.archive_url,
        "error": submission.error,
        "tries": submission.attempts,
        "created_at": submission.created_at,
        "submitted_at": submission.submitted_at,
    }
