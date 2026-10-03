from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get
from ..models import Domain, Submission, URL

r = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@r.get("")
def dash(db: Session = Depends(get)):
    return {
        "domains": db.scalar(select(func.count(Domain.id))) or 0,
        "urls": db.scalar(select(func.count(URL.id))) or 0,
        "queued": db.scalar(
            select(func.count(Submission.id)).where(
                Submission.status.in_(["queued", "processing", "retry"])
            )
        ) or 0,
        "submitted": db.scalar(
            select(func.count(Submission.id)).where(
                Submission.status == "success"
            )
        ) or 0,
        "success": db.scalar(
            select(func.count(Submission.id)).where(
                Submission.status == "success"
            )
        ) or 0,
        "failed": db.scalar(
            select(func.count(Submission.id)).where(
                Submission.status == "failed"
            )
        ) or 0,
        "pending": db.scalar(
            select(func.count(Submission.id)).where(
                Submission.status == "queued"
            )
        ) or 0,
        "manual": db.scalar(
            select(func.count(Submission.id)).where(
                Submission.status == "manual"
            )
        ) or 0,
    }
