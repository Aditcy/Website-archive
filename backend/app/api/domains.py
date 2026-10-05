from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get
from ..models import Domain
from ..schemas.domain import DomIn, DomOut
from ..services.crawl_service import start


r = APIRouter(prefix="/api/domains", tags=["domains"])


@r.post("", response_model=DomOut)
def create(x: DomIn, db: Session = Depends(get)):
    value = x.url.strip().rstrip("/")
    parsed = urlsplit(value)

    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise HTTPException(422, "invalid HTTP/HTTPS URL")

    name = parsed.hostname.lower()

    existing = db.execute(
        select(Domain).where(Domain.name == name)
    ).scalar_one_or_none()

    if existing:
        return existing

    domain = Domain(
        name=name,
        base_url=value,
        active=True,
    )

    db.add(domain)
    db.commit()
    db.refresh(domain)

    return domain


@r.get("", response_model=list[DomOut])
def all(db: Session = Depends(get)):
    return (
        db.execute(
            select(Domain).order_by(Domain.id.desc())
        )
        .scalars()
        .all()
    )


@r.get("/{did}", response_model=DomOut)
def one(did: int, db: Session = Depends(get)):
    domain = db.get(Domain, did)

    if not domain:
        raise HTTPException(404, "domain not found")

    return domain


@r.patch("/{did}/active")
def set_active(
    did: int,
    active: bool,
    db: Session = Depends(get),
):
    domain = db.get(Domain, did)

    if not domain:
        raise HTTPException(404, "domain not found")

    domain.active = active
    db.commit()
    db.refresh(domain)

    return {
        "id": domain.id,
        "active": domain.active,
    }


@r.delete("/{did}")
def delete(did: int, db: Session = Depends(get)):
    domain = db.get(Domain, did)

    if not domain:
        raise HTTPException(404, "domain not found")

    db.delete(domain)
    db.commit()

    return {
        "deleted": True,
        "id": did,
    }


@r.post("/{did}/scan")
def scan(did: int, db: Session = Depends(get)):
    domain = db.get(Domain, did)

    if not domain:
        raise HTTPException(404, "domain not found")

    if not domain.active:
        raise HTTPException(409, "domain is inactive")

    crawl = start(db, did)

    return {
        "crawl_id": crawl.id,
        "status": crawl.status,
    }
