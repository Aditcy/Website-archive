from datetime import datetime
from sqlalchemy import select
from ..models import Domain,Crawl
from ..workers.tasks import crawl

def start(db,did):
    c=Crawl(domain_id=did);db.add(c);db.commit();db.refresh(c);crawl.delay(did,c.id);return c
