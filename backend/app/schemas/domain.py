from datetime import datetime

from pydantic import AnyHttpUrl, BaseModel, ConfigDict


class DomIn(BaseModel):
    url: AnyHttpUrl


class DomOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    base_url: str
    active: bool
    created_at: datetime
    last_scan: datetime | None = None
    last_submit: datetime | None = None
