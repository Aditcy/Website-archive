from datetime import datetime

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, TypeAdapter, field_validator


_http_url_adapter = TypeAdapter(AnyHttpUrl)


class DomIn(BaseModel):
    url: str

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("URL must not be empty")

        # Validate as an HTTP/HTTPS URL, but return the original
        # string so hostname casing is preserved.
        _http_url_adapter.validate_python(value)

        return value


class DomOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    base_url: str
    active: bool
    created_at: datetime
    last_scan: datetime | None = None
    last_submit: datetime | None = None
