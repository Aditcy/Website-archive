from datetime import datetime
from ..time import utcnow
from sqlalchemy import String,DateTime,Text,Boolean,Integer
from sqlalchemy.orm import Mapped,mapped_column,relationship
from ..db import Base

class Domain(Base):
    __tablename__ = "domains"

    id: Mapped[int] = mapped_column(Integer,primary_key=True)
    name: Mapped[str] = mapped_column(String(253),unique=True,index=True)
    base_url: Mapped[str] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean,default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime,default=utcnow)
    last_scan: Mapped[datetime | None] = mapped_column(DateTime)
    last_submit: Mapped[datetime | None] = mapped_column(DateTime)

    urls = relationship("URL",back_populates="domain",cascade="all,delete-orphan")
