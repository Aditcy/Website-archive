from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select
from ..db import get
from ..models import Domain
from ..schemas.domain import DomIn,DomOut
from ..services.crawl_service import start

r=APIRouter(prefix="/api/domains",tags=["domains"])

@r.post("",response_model=DomOut)
def create(x:DomIn,db:Session=Depends(get)):
    u=str(x.url).rstrip("/")
    from urllib.parse import urlsplit
    name=urlsplit(u).hostname.lower()
    q=db.execute(select(Domain).where(Domain.name==name)).scalar_one_or_none()
    if q:return q
    d=Domain(name=name,base_url=u);db.add(d);db.commit();db.refresh(d);return d

@r.get("",response_model=list[DomOut])
def all(db:Session=Depends(get)):return db.execute(select(Domain).order_by(Domain.id.desc())).scalars().all()

@r.post("/{did}/scan")
def scan(did:int,db:Session=Depends(get)):
    if not db.get(Domain,did):raise HTTPException(404,"domain not found")
    c=start(db,did);return {"crawl_id":c.id,"status":c.status}
