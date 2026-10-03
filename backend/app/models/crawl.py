from datetime import datetime
from sqlalchemy import String,DateTime,Integer,ForeignKey,Text
from sqlalchemy.orm import Mapped,mapped_column,relationship
from ..db import Base

class Crawl(Base):
    __tablename__ = "crawls"

    id: Mapped[int] = mapped_column(Integer,primary_key=True)
    domain_id: Mapped[int] = mapped_column(ForeignKey("domains.id",ondelete="CASCADE"),index=True)
    status: Mapped[str] = mapped_column(String(30),default="queued",index=True)
    total: Mapped[int] = mapped_column(Integer,default=0)
    done: Mapped[int] = mapped_column(Integer,default=0)
    failed: Mapped[int] = mapped_column(Integer,default=0)
    error: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
    heartbeat: Mapped[datetime | None] = mapped_column(DateTime)

    domain = relationship("Domain")
