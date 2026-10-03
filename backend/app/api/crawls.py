from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get
from ..models import Crawl

r = APIRouter(prefix="/api/crawls", tags=["crawls"])


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
