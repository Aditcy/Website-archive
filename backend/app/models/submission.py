from datetime import datetime

from sqlalchemy import (
    String,
    DateTime,
    Integer,
    ForeignKey,
    Text,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from ..time import utcnow
from ..db import Base


class Submission(Base):
    __tablename__ = "submissions"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    url_id: Mapped[int] = mapped_column(
        ForeignKey(
            "urls.id",
            ondelete="CASCADE",
        ),
        index=True,
    )

    service: Mapped[str] = mapped_column(
        String(50),
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        default="queued",
        index=True,
    )

    archive_url: Mapped[str | None] = mapped_column(
        Text,
    )

    error: Mapped[str | None] = mapped_column(
        Text,
    )

    attempts: Mapped[int] = mapped_column(
        Integer,
        default=0,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utcnow,
    )

    submitted_at: Mapped[datetime | None] = mapped_column(
        DateTime,
    )

    url = relationship(
        "URL",
        back_populates="submissions",
    )
