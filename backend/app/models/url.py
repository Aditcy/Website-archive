from datetime import datetime
from ..time import utcnow
from sqlalchemy import String,DateTime,Text,Integer,ForeignKey,Boolean
from sqlalchemy.orm import Mapped,mapped_column,relationship
from ..db import Base

class URL(Base):
    __tablename__ = "urls"

    id: Mapped[int] = mapped_column(Integer,primary_key=True)
    domain_id: Mapped[int] = mapped_column(ForeignKey("domains.id",ondelete="CASCADE"),index=True)
    url: Mapped[str] = mapped_column(Text,index=True)
    norm: Mapped[str] = mapped_column(Text,index=True)
    status: Mapped[str] = mapped_column(String(30),default="discovered",index=True)
    http_status: Mapped[int | None] = mapped_column(Integer)
    content_type: Mapped[str | None] = mapped_column(String(200))
    redirect: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str | None] = mapped_column(String(30))
    discovered_at: Mapped[datetime] = mapped_column(DateTime,default=utcnow)
    crawled_at: Mapped[datetime | None] = mapped_column(DateTime)
    checked_at: Mapped[datetime | None] = mapped_column(DateTime)
    queued: Mapped[bool] = mapped_column(Boolean,default=False,index=True)

    domain = relationship("Domain",back_populates="urls")
    submissions = relationship("Submission",back_populates="url",cascade="all,delete-orphan")
