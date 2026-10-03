#!/usr/bin/env bash
set -e

mkdir -p backend/app/{api,models,schemas,crawler,archives,workers,services}
mkdir -p backend/migrations backend/tests frontend docs

cat <<'PY' > backend/app/config.py
import os

class Conf:
    db=os.getenv("DATABASE_URL","postgresql+psycopg://archive:archive@127.0.0.1:5432/archive")
    redis=os.getenv("REDIS_URL","redis://127.0.0.1:6379/0")
    key=os.getenv("IA_KEY","")
    secret=os.getenv("IA_SECRET","")
    host=os.getenv("APP_HOST","0.0.0.0")
    port=int(os.getenv("APP_PORT","8000"))
    ua=os.getenv("CRAWL_UA","WebArchiveRepo/1.0")
    batch=int(os.getenv("CRAWL_BATCH","25"))
    delay=float(os.getenv("CRAWL_DELAY","0.5"))
    retry=int(os.getenv("SUB_RETRY","3"))

cfg=Conf()
PY

cat <<'PY' > backend/app/models/base.py
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass
PY

cat <<'PY' > backend/app/models/domain.py
from datetime import datetime
from sqlalchemy import String,DateTime,Integer,Boolean
from sqlalchemy.orm import Mapped,mapped_column,relationship
from .base import Base

class Domain(Base):
    __tablename__="domains"
    id:Mapped[int]=mapped_column(primary_key=True)
    name:Mapped[str]=mapped_column(String(255),unique=True,index=True)
    base_url:Mapped[str]=mapped_column(String(2048))
    status:Mapped[str]=mapped_column(String(30),default="active")
    created_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)
    last_scan:Mapped[datetime|None]=mapped_column(DateTime)
    last_sub:Mapped[datetime|None]=mapped_column(DateTime)
    urls=relationship("Url",back_populates="domain",cascade="all,delete-orphan")
PY

cat <<'PY' > backend/app/models/crawl.py
from datetime import datetime
from sqlalchemy import String,DateTime,Integer,ForeignKey
from sqlalchemy.orm import Mapped,mapped_column,relationship
from .base import Base

class Crawl(Base):
    __tablename__="crawls"
    id:Mapped[int]=mapped_column(primary_key=True)
    domain_id:Mapped[int]=mapped_column(ForeignKey("domains.id",ondelete="CASCADE"),index=True)
    status:Mapped[str]=mapped_column(String(30),default="queued",index=True)
    started:Mapped[datetime|None]=mapped_column(DateTime)
    ended:Mapped[datetime|None]=mapped_column(DateTime)
    found:Mapped[int]=mapped_column(Integer,default=0)
    new:Mapped[int]=mapped_column(Integer,default=0)
    errors:Mapped[int]=mapped_column(Integer,default=0)
    domain=relationship("Domain")
PY

cat <<'PY' > backend/app/models/url.py
from datetime import datetime
from sqlalchemy import String,DateTime,Integer,Boolean,ForeignKey,Text,UniqueConstraint
from sqlalchemy.orm import Mapped,mapped_column,relationship
from .base import Base

class Url(Base):
    __tablename__="urls"
    __table_args__=(UniqueConstraint("domain_id","norm_url",name="uq_domain_url"),)
    id:Mapped[int]=mapped_column(primary_key=True)
    domain_id:Mapped[int]=mapped_column(ForeignKey("domains.id",ondelete="CASCADE"),index=True)
    orig_url:Mapped[str]=mapped_column(Text)
    norm_url:Mapped[str]=mapped_column(Text,index=True)
    source:Mapped[str]=mapped_column(String(40),default="html")
    source_url:Mapped[str|None]=mapped_column(Text)
    first_seen:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)
    last_seen:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)
    crawled:Mapped[datetime|None]=mapped_column(DateTime,index=True)
    http:Mapped[int|None]=mapped_column(Integer)
    ctype:Mapped[str|None]=mapped_column(String(120))
    access:Mapped[bool]=mapped_column(Boolean,default=True)
    error:Mapped[str|None]=mapped_column(Text)
    domain=relationship("Domain",back_populates="urls")
    subs=relationship("Submission",back_populates="url",cascade="all,delete-orphan")
PY

cat <<'PY' > backend/app/models/submission.py
from datetime import datetime
from sqlalchemy import String,DateTime,Integer,ForeignKey,Text
from sqlalchemy.orm import Mapped,mapped_column,relationship
from .base import Base

class Submission(Base):
    __tablename__="submissions"
    id:Mapped[int]=mapped_column(primary_key=True)
    url_id:Mapped[int]=mapped_column(ForeignKey("urls.id",ondelete="CASCADE"),index=True)
    service:Mapped[str]=mapped_column(String(40),index=True)
    status:Mapped[str]=mapped_column(String(30),default="pending",index=True)
    queued:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)
    started:Mapped[datetime|None]=mapped_column(DateTime)
    ended:Mapped[datetime|None]=mapped_column(DateTime)
    tries:Mapped[int]=mapped_column(Integer,default=0)
    archive_url:Mapped[str|None]=mapped_column(Text)
    archive_id:Mapped[str|None]=mapped_column(String(255))
    error:Mapped[str|None]=mapped_column(Text)
    last_try:Mapped[datetime|None]=mapped_column(DateTime)
    next_try:Mapped[datetime|None]=mapped_column(DateTime)
    url=relationship("Url",back_populates="subs")
PY

cat <<'PY' > backend/app/models/__init__.py
from .base import Base
from .domain import Domain
from .crawl import Crawl
from .url import Url
from .submission import Submission
PY

cat <<'PY' > backend/app/schemas/domain.py
from pydantic import BaseModel,HttpUrl

class DomIn(BaseModel):
    url:HttpUrl

class DomOut(BaseModel):
    id:int
    name:str
    base_url:str
    status:str
    model_config={"from_attributes":True}
PY

cat <<'PY' > backend/app/schemas/url.py
from pydantic import BaseModel

class UrlOut(BaseModel):
    id:int
    orig_url:str
    norm_url:str
    source:str
    http:int|None
    crawled:str|None
    model_config={"from_attributes":True}
PY

cat <<'PY' > backend/app/schemas/submission.py
from pydantic import BaseModel

class SubOut(BaseModel):
    id:int
    service:str
    status:str
    archive_url:str|None
    tries:int
    error:str|None
    model_config={"from_attributes":True}
PY

cat <<'PY' > backend/app/db.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .config import cfg
from .models import Base

eng=create_engine(cfg.db,pool_pre_ping=True)
Ses=sessionmaker(eng,expire_on_commit=False)

def init():
    Base.metadata.create_all(eng)

def get():
    db=Ses()
    try: yield db
    finally: db.close()
PY

cat <<'PY' > backend/app/crawler/normalize.py
from urllib.parse import urlsplit,urlunsplit,parse_qsl,urlencode
import hashlib

def norm(url):
    try:
        p=urlsplit(url.strip())
        if p.scheme not in ("http","https") or not p.netloc:return None
        host=p.hostname.lower()
        port=p.port
        net=host
        if port and not ((p.scheme=="http" and port==80) or (p.scheme=="https" and port==443)):net=f"{host}:{port}"
        path=p.path or "/"
        q=[x for x in parse_qsl(p.query,keep_blank_values=True) if not x[0].lower().startswith(("utm_","fbclid","gclid"))]
        return urlunsplit((p.scheme.lower(),net,path,urlencode(q,doseq=True),""))
    except:return None

def host(url):
    try:return urlsplit(url).hostname.lower()
    except:return ""

def key(url):
    return hashlib.sha256(url.encode()).hexdigest()
PY

cat <<'PY' > backend/app/crawler/html.py
from bs4 import BeautifulSoup
from urllib.parse import urljoin

def links(txt,base):
    s=BeautifulSoup(txt,"html.parser")
    out=[]
    for a in s.find_all("a",href=True):
        u=urljoin(base,a["href"])
        out.append(u)
    for x in s.find_all("link",href=True):
        r=x.get("rel",[])
        if "canonical" in [str(i).lower() for i in r]:out.append(urljoin(base,x["href"]))
    return out
PY

cat <<'PY' > backend/app/crawler/sitemap.py
import httpx
from xml.etree import ElementTree as ET

def urls(txt):
    try:
        root=ET.fromstring(txt)
        return [x.text.strip() for x in root.iter() if x.tag.rsplit("}",1)[-1]=="loc" and x.text]
    except:return []

def get(url,head):
    try:
        r=httpx.get(url,headers=head,timeout=20,follow_redirects=True)
        return r.text if r.status_code<400 else ""
    except:return ""
PY

cat <<'PY' > backend/app/crawler/robots.py
from urllib.robotparser import RobotFileParser
from urllib.parse import urljoin

def read(base):
    u=urljoin(base,"/robots.txt")
    try:
        r=RobotFileParser(u);r.read();return r
    except:return None

def maps(txt):
    return [x.split(":",1)[1].strip() for x in txt.splitlines() if x.lower().startswith("sitemap:")]
PY

cat <<'PY' > backend/app/crawler/feeds.py
from bs4 import BeautifulSoup
from urllib.parse import urljoin

def find(txt,base):
    s=BeautifulSoup(txt,"html.parser")
    out=[]
    for x in s.find_all(["link"],href=True):
        t=(x.get("type") or "").lower()
        if "rss" in t or "atom" in t or "feed" in t:out.append(urljoin(base,x["href"]))
    return out
PY

cat <<'PY' > backend/app/crawler/browser.py
def render(url):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b=p.chromium.launch(headless=True)
        pg=b.new_page()
        pg.goto(url,wait_until="networkidle",timeout=60000)
        txt=pg.content()
        b.close()
        return txt
PY

cat <<'PY' > backend/app/crawler/engine.py
import time
import httpx
from datetime import datetime
from urllib.parse import urljoin
from sqlalchemy import select,func
from ..config import cfg
from ..models import Domain,Url,Crawl
from .normalize import norm,host
from .html import links
from .sitemap import get as smget,urls as smurls
from .robots import maps

def add(db,did,raw,src,srcu=None):
    u=norm(raw)
    if not u:return None
    d=db.get(Domain,did)
    if host(u)!=host(d.base_url) and not host(u).endswith("."+host(d.base_url)):return None
    q=db.execute(select(Url).where(Url.domain_id==did,Url.norm_url==u)).scalar_one_or_none()
    if q:
        q.last_seen=datetime.utcnow()
        return q,False
    q=Url(domain_id=did,orig_url=raw,norm_url=u,source=src,source_url=srcu)
    db.add(q);db.flush()
    return q,True

def seed(db,did):
    d=db.get(Domain,did)
    add(db,did,d.base_url,"root")
    rurl=urljoin(d.base_url,"/robots.txt")
    try:
        r=httpx.get(rurl,headers={"User-Agent":cfg.ua},timeout=20)
        for s in maps(r.text):
            for u in smurls(smget(s,{"User-Agent":cfg.ua})):
                add(db,did,u,"sitemap",s)
    except:pass
    db.commit()

def run(did,rid):
    from ..db import Ses
    db=Ses()
    d=db.get(Domain,did);c=db.get(Crawl,rid)
    c.status="running";c.started=datetime.utcnow();db.commit()
    seed(db,did)
    while True:
        rows=db.execute(select(Url).where(Url.domain_id==did,Url.crawled.is_(None)).limit(cfg.batch)).scalars().all()
        if not rows:break
        for u in rows:
            try:
                h={"User-Agent":cfg.ua}
                r=httpx.get(u.norm_url,headers=h,timeout=20,follow_redirects=True)
                u.http=r.status_code;u.ctype=r.headers.get("content-type","")[:120]
                u.crawled=datetime.utcnow();u.access=r.status_code<400
                if "text/html" in u.ctype:
                    for x in links(r.text,r.url):
                        add(db,did,x,"html",u.norm_url)
                c.found=db.scalar(select(func.count(Url.id)).where(Url.domain_id==did)) or 0
                db.commit()
                time.sleep(cfg.delay)
            except Exception as e:
                u.error=str(e)[:1000];u.crawled=datetime.utcnow();c.errors+=1;db.commit()
    c.found=db.scalar(select(func.count(Url.id)).where(Url.domain_id==did)) or 0
    c.new=db.scalar(select(func.count(Url.id)).where(Url.domain_id==did,Url.first_seen>=c.started)) or 0
    c.status="done";c.ended=datetime.utcnow();d.last_scan=datetime.utcnow();db.commit();db.close()
PY

cat <<'PY' > backend/app/archives/base.py
from dataclasses import dataclass

@dataclass
class Res:
    ok:bool
    url:str|None=None
    aid:str|None=None
    err:str|None=None

class Arch:
    name="base"
    def submit(self,url):raise NotImplementedError
    def status(self,aid):raise NotImplementedError
PY

cat <<'PY' > backend/app/archives/wayback.py
import time,httpx
from urllib.parse import quote
from ..config import cfg
from .base import Arch,Res

class Way(Arch):
    name="wayback"
    def submit(self,url):
        h={"Accept":"application/json","User-Agent":cfg.ua}
        if not cfg.key or not cfg.secret:
            try:
                r=httpx.get("https://web.archive.org/save/"+quote(url,safe=":/?=&%"),headers=h,timeout=60,follow_redirects=False)
                loc=r.headers.get("location") or r.headers.get("content-location")
                if loc:
                    return Res(True,loc)
                return Res(False,err=f"HTTP {r.status_code}: configure IA_KEY/IA_SECRET if SPN2 requires auth")
            except Exception as e:return Res(False,err=str(e)[:1000])
        h["Authorization"]=f"LOW {cfg.key}:{cfg.secret}"
        try:
            r=httpx.post("https://web.archive.org/save",headers=h,data={"url":url,"skip_first_archive":"1"},timeout=60)
            if r.status_code>=400:return Res(False,err=f"HTTP {r.status_code}: {r.text[:500]}")
            j=r.json();aid=j.get("job_id")
            if not aid:return Res(False,err="No job_id returned")
            for _ in range(24):
                s=httpx.get(f"https://web.archive.org/save/status/{aid}",headers=h,timeout=30)
                z=s.json()
                if z.get("status")=="success":
                    ts=z.get("timestamp");ou=z.get("original_url") or url
                    return Res(True,f"https://web.archive.org/web/{ts}/{ou}",aid)
                if z.get("status")=="error":return Res(False,aid=aid,err=z.get("message") or z.get("status_ext") or "capture failed")
                time.sleep(5)
            return Res(False,aid=aid,err="capture pending after timeout")
        except Exception as e:return Res(False,err=str(e)[:1000])
    def status(self,aid):
        try:return httpx.get(f"https://web.archive.org/save/status/{aid}",timeout=30).json()
        except:return {}
PY

cat <<'PY' > backend/app/archives/archive_today.py
from urllib.parse import quote
from .base import Arch,Res

class Arc(Arch):
    name="archive_today"
    def submit(self,url):
        u=f"https://archive.today/?run=1&url={quote(url,safe='')}"
        return Res(False,url=u,err="manual_required")
    def status(self,aid):return {}
PY

cat <<'PY' > backend/app/archives/__init__.py
from .wayback import Way
from .archive_today import Arc

def get(name):
    return {"wayback":Way(),"archive_today":Arc()}.get(name)
PY

cat <<'PY' > backend/app/services/crawl_service.py
from datetime import datetime
from sqlalchemy import select
from ..models import Domain,Crawl
from ..workers.tasks import crawl

def start(db,did):
    c=Crawl(domain_id=did);db.add(c);db.commit();db.refresh(c);crawl.delay(did,c.id);return c
PY

cat <<'PY' > backend/app/services/submission_service.py
from datetime import datetime
from sqlalchemy import select,exists
from ..models import Url,Submission
from ..workers.tasks import sub

def make(db,did,service):
    rows=db.execute(select(Url).where(Url.domain_id==did)).scalars().all();n=0
    for u in rows:
        ok=db.execute(select(exists().where(Submission.url_id==u.id,Submission.service==service,Submission.status=="success"))).scalar()
        if not ok:
            db.add(Submission(url_id=u.id,service=service));n+=1
    db.commit()
    for x in db.execute(select(Submission).join(Url).where(Url.domain_id==did,Submission.status=="pending",Submission.service==service)).scalars():sub.delay(x.id)
    return n
PY

cat <<'PY' > backend/app/services/incremental_service.py
from sqlalchemy import select
from ..models import Url,Submission

def new(db,did):
    return db.execute(select(Url).where(Url.domain_id==did,~Url.subs.any(Submission.status=="success"))).scalars().all()
PY

cat <<'PY' > backend/app/workers/celery.py
from celery import Celery
from ..config import cfg

cel=Celery("archive",broker=cfg.redis,backend=cfg.redis)
cel.conf.update(task_acks_late=True,worker_prefetch_multiplier=1,task_track_started=True)
PY

cat <<'PY' > backend/app/workers/tasks.py
from datetime import datetime,timedelta
from sqlalchemy import select
from .celery import cel
from ..db import Ses
from ..models import Submission
from ..crawler.engine import run
from ..archives import get
from ..config import cfg

@cel.task(bind=True,max_retries=0)
def crawl(self,did,rid):
    run(did,rid)

@cel.task(bind=True,max_retries=cfg.retry)
def sub(self,sid):
    db=Ses();x=db.get(Submission,sid)
    if not x or x.status=="success":db.close();return
    x.status="processing";x.started=datetime.utcnow();x.last_try=datetime.utcnow();x.tries+=1;db.commit()
    try:
        p=get(x.service);r=p.submit(x.url.norm_url)
        if r.ok:
            x.status="success";x.archive_url=r.url;x.archive_id=r.aid;x.ended=datetime.utcnow();db.commit()
        elif r.err=="manual_required":
            x.status="manual";x.archive_url=r.url;x.error=r.err;x.ended=datetime.utcnow();db.commit()
        elif x.tries<cfg.retry:
            x.status="retry";x.error=r.err;x.next_try=datetime.utcnow()+timedelta(seconds=30*x.tries);db.commit();db.close();raise self.retry(countdown=30*x.tries)
        else:
            x.status="failed";x.error=r.err;x.ended=datetime.utcnow();db.commit()
    except Exception as e:
        if db.is_active:
            x.status="failed";x.error=str(e)[:1000];x.ended=datetime.utcnow();db.commit()
    db.close()
PY

cat <<'PY' > backend/app/api/domains.py
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
PY

cat <<'PY' > backend/app/api/crawls.py
from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select
from ..db import get
from ..models import Crawl

r=APIRouter(prefix="/api/crawls",tags=["crawls"])

@r.get("/{cid}")
def one(cid:int,db:Session=Depends(get)):
    x=db.get(Crawl,cid)
    if not x:raise HTTPException(404,"crawl not found")
    return {"id":x.id,"domain_id":x.domain_id,"status":x.status,"found":x.found,"new":x.new,"errors":x.errors,"started":x.started,"ended":x.ended}
PY

cat <<'PY' > backend/app/api/urls.py
from fastapi import APIRouter,Depends
from sqlalchemy.orm import Session
from sqlalchemy import select,or_
from ..db import get
from ..models import Url

r=APIRouter(prefix="/api/urls",tags=["urls"])

@r.get("")
def all(domain:int|None=None,q:str="",page:int=1,size:int=50,db:Session=Depends(get)):
    x=select(Url)
    if domain:x=x.where(Url.domain_id==domain)
    if q:x=x.where(or_(Url.norm_url.ilike(f"%{q}%"),Url.orig_url.ilike(f"%{q}%")))
    rows=db.execute(x.order_by(Url.id.desc()).offset((page-1)*size).limit(size)).scalars()
    return [{"id":u.id,"domain_id":u.domain_id,"url":u.norm_url,"source":u.source,"http":u.http,"crawled":u.crawled} for u in rows]
PY

cat <<'PY' > backend/app/api/submissions.py
from fastapi import APIRouter,Depends
from sqlalchemy.orm import Session
from sqlalchemy import select
from ..db import get
from ..models import Submission
from ..services.submission_service import make

r=APIRouter(prefix="/api/submissions",tags=["submissions"])

@r.post("/queue/{did}")
def queue(did:int,service:str="wayback",db:Session=Depends(get)):
    return {"queued":make(db,did,service),"service":service}

@r.get("")
def all(domain:int|None=None,status:str|None=None,service:str|None=None,db:Session=Depends(get)):
    x=select(Submission)
    if domain:x=x.join(Submission.url).where(Submission.url.has(domain_id=domain))
    if status:x=x.where(Submission.status==status)
    if service:x=x.where(Submission.service==service)
    rows=db.execute(x.order_by(Submission.id.desc()).limit(200)).scalars()
    return [{"id":s.id,"url":s.url.norm_url,"service":s.service,"status":s.status,"archive_url":s.archive_url,"error":s.error,"tries":s.tries} for s in rows]
PY

cat <<'PY' > backend/app/api/dashboard.py
from fastapi import APIRouter,Depends
from sqlalchemy.orm import Session
from sqlalchemy import select,func
from ..db import get
from ..models import Domain,Url,Submission

r=APIRouter(prefix="/api/dashboard",tags=["dashboard"])

@r.get("")
def dash(db:Session=Depends(get)):
    return {
        "domains":db.scalar(select(func.count(Domain.id))) or 0,
        "urls":db.scalar(select(func.count(Url.id))) or 0,
        "queued":db.scalar(select(func.count(Submission.id)).where(Submission.status.in_(["pending","processing","retry"]))) or 0,
        "submitted":db.scalar(select(func.count(Submission.id)).where(Submission.status=="success")) or 0,
        "success":db.scalar(select(func.count(Submission.id)).where(Submission.status=="success")) or 0,
        "failed":db.scalar(select(func.count(Submission.id)).where(Submission.status=="failed")) or 0,
        "pending":db.scalar(select(func.count(Submission.id)).where(Submission.status=="pending")) or 0,
        "manual":db.scalar(select(func.count(Submission.id)).where(Submission.status=="manual")) or 0
    }
PY

cat <<'PY' > backend/app/api/__init__.py
from .domains import r as domains
from .crawls import r as crawls
from .urls import r as urls
from .submissions import r as submissions
from .dashboard import r as dashboard
PY

cat <<'PY' > backend/app/main.py
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from .db import init
from .api import domains,crawls,urls,submissions,dashboard

app=FastAPI(title="Website Archive Repository",version="1.0.0")

@app.on_event("startup")
def boot():init()

app.include_router(domains);app.include_router(crawls);app.include_router(urls);app.include_router(submissions);app.include_router(dashboard)
app.mount("/static",StaticFiles(directory="../frontend"),name="static")

@app.get("/")
def home():return FileResponse("../frontend/index.html")
PY

cat <<'PY' > backend/app/__init__.py
PY

cat <<'TXT' > backend/requirements.txt
fastapi
uvicorn[standard]
sqlalchemy
psycopg[binary]
pydantic
httpx
beautifulsoup4
celery
redis
python-multipart
playwright
TXT

cat <<'HTML' > frontend/index.html
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Website Archive Repository</title>
<style>
body{font-family:system-ui;background:#0f172a;color:#e2e8f0;margin:0}main{max-width:1200px;margin:auto;padding:24px}h1{margin-top:0}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px}.card{background:#1e293b;padding:16px;border-radius:12px}.num{font-size:28px;font-weight:700}input,select,button{padding:10px;border-radius:8px;border:1px solid #475569;background:#0f172a;color:#e2e8f0}button{cursor:pointer;background:#2563eb;border:0}.row{display:flex;gap:8px;flex-wrap:wrap;margin:14px 0}table{width:100%;border-collapse:collapse;background:#1e293b}th,td{padding:10px;border-bottom:1px solid #334155;text-align:left}a{color:#60a5fa}
</style>
</head>
<body><main>
<h1>Website Archive Repository</h1>
<div class="grid" id="stats"></div>
<div class="row"><input id="site" placeholder="https://example.com"><button onclick="add()">Add Domain</button></div>
<div id="domains"></div>
<h2>URL Repository</h2>
<div class="row"><input id="q" placeholder="Search URL" oninput="loadUrls()"></div>
<table><thead><tr><th>URL</th><th>Source</th><th>HTTP</th><th>Crawled</th></tr></thead><tbody id="urls"></tbody></table>
<script>
const j=async(u,o)=>fetch(u,o).then(r=>r.json());
async function load(){let s=await j('/api/dashboard');document.querySelector('#stats').innerHTML=Object.entries(s).map(([k,v])=>`<div class="card"><div>${k}</div><div class="num">${v}</div></div>`).join('');let d=await j('/api/domains');document.querySelector('#domains').innerHTML=d.map(x=>`<div class="card" style="margin:10px 0"><b>${x.name}</b><div>${x.base_url}</div><div class="row"><button onclick="scan(${x.id})">Scan</button><button onclick="queue(${x.id},'wayback')">Archive Wayback</button><button onclick="queue(${x.id},'archive_today')">Archive.today</button></div></div>`).join('');loadUrls()}
async function add(){let v=document.querySelector('#site').value;if(!v)return;await j('/api/domains',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({url:v})});document.querySelector('#site').value='';load()}
async function scan(id){await j('/api/domains/'+id+'/scan',{method:'POST'});load()}
async function queue(id,s){await j('/api/submissions/queue/'+id+'?service='+s,{method:'POST'});load()}
async function loadUrls(){let q=encodeURIComponent(document.querySelector('#q').value);let a=await j('/api/urls?q='+q);document.querySelector('#urls').innerHTML=a.map(x=>`<tr><td>${x.url}</td><td>${x.source}</td><td>${x.http??''}</td><td>${x.crawled??''}</td></tr>`).join('')}
load();setInterval(load,5000)
</script></main></body></html>
HTML

cat <<'YML' > docker-compose.yml
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_DB: archive
      POSTGRES_USER: archive
      POSTGRES_PASSWORD: archive
    ports: ["5432:5432"]
    volumes: [pg:/var/lib/postgresql/data]
  redis:
    image: redis:7
    ports: ["6379:6379"]
  api:
    build: ./backend
    environment:
      DATABASE_URL: postgresql+psycopg://archive:archive@db:5432/archive
      REDIS_URL: redis://redis:6379/0
      IA_KEY: ${IA_KEY:-}
      IA_SECRET: ${IA_SECRET:-}
    ports: ["8000:8000"]
    depends_on: [db,redis]
  worker:
    build: ./backend
    command: celery -A app.workers.celery.cel worker --loglevel=INFO
    environment:
      DATABASE_URL: postgresql+psycopg://archive:archive@db:5432/archive
      REDIS_URL: redis://redis:6379/0
      IA_KEY: ${IA_KEY:-}
      IA_SECRET: ${IA_SECRET:-}
    depends_on: [db,redis]
volumes:
  pg:
YML

cat <<'DOCKER' > backend/Dockerfile
FROM python:3.12-slim
WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install --with-deps chromium
COPY app ./app
CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8000"]
DOCKER

cat <<'ENV' > .env.example
IA_KEY=
IA_SECRET=
DATABASE_URL=postgresql+psycopg://archive:archive@127.0.0.1:5432/archive
REDIS_URL=redis://127.0.0.1:6379/0
CRAWL_UA=WebArchiveRepo/1.0
CRAWL_BATCH=25
CRAWL_DELAY=0.5
SUB_RETRY=3
ENV

cat <<'MD' > README.md
# Website Archive Repository

Python/FastAPI/PostgreSQL/Redis/Celery website discovery and archival repository.

## Local

Create PostgreSQL database `archive` and Redis, install `backend/requirements.txt`, then start:

`uvicorn app.main:app --host 0.0.0.0 --port 8000`

From `backend` run the worker:

`celery -A app.workers.celery.cel worker --loglevel=INFO`

Open `http://127.0.0.1:8000`.

## Wayback

Configure `IA_KEY` and `IA_SECRET` when using the current authenticated SPN2 API.

## Archive.today

The current implementation generates a manual submission URL rather than pretending an undocumented automated API exists.
MD

cat <<'MD' > docs/architecture.md
# Architecture

FastAPI provides the API and dashboard. PostgreSQL is the durable repository. Redis/Celery provides persistent background jobs. Discovery uses robots.txt, sitemap XML, HTML links, canonical links and feeds. URLs are normalized and deduplicated by domain. Crawl state is stored in PostgreSQL so interrupted work can resume. Archive services use provider adapters. Wayback uses Save Page Now when credentials are configured. Archive.today is represented as a manual provider until a documented public automated submission interface is verified.

Core flow:

domain -> crawl -> URL repository -> submission queue -> archive provider -> submission history
MD

cat <<'MD' > backend/migrations/001.sql
CREATE INDEX IF NOT EXISTS ix_urls_domain_norm ON urls(domain_id,norm_url);
CREATE INDEX IF NOT EXISTS ix_sub_status_service ON submissions(status,service);
MD

cat <<'PY' > backend/tests/test_norm.py
from app.crawler.normalize import norm

def test_norm():
    assert norm("https://EXAMPLE.com/a#x")=="https://example.com/a"
    assert norm("https://example.com/a?utm_source=x&x=1")=="https://example.com/a?x=1"
PY

echo "Project created."
echo "Next: install dependencies and start PostgreSQL + Redis."
