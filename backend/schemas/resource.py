from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, field_validator


def _validate_http_url(v: str) -> str:
    if not (v.startswith("http://") or v.startswith("https://")):
        raise ValueError("URL must start with http:// or https://")
    return v


class ResourceCreate(BaseModel):
    title: str
    url: str
    description: Optional[str] = None

    @field_validator("url")
    @classmethod
    def check_url(cls, v: str) -> str:
        return _validate_http_url(v)


class ResourceUpdate(BaseModel):
    title: Optional[str] = None
    url: Optional[str] = None
    description: Optional[str] = None

    @field_validator("url")
    @classmethod
    def check_url(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        return _validate_http_url(v)


class ResourceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    resource_id: int
    section_id: int
    teacher_id: int
    title: str
    url: str
    description: Optional[str] = None
    created_at: datetime
