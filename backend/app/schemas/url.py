from datetime import datetime
from pydantic import BaseModel, ConfigDict


class UrlOut(BaseModel):
    id: int
    domain_id: int
    url: str
    norm: str
    status: str
    http_status: int | None = None
    content_type: str | None = None
    redirect: str | None = None
    source: str | None = None
    discovered_at: datetime
    crawled_at: datetime | None = None
    checked_at: datetime | None = None
    queued: bool

    model_config = ConfigDict(from_attributes=True)
