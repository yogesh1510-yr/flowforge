import re
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    slug: str = Field(min_length=1, max_length=120)
    parent_id: UUID | None = None

    @field_validator("name", "slug")
    @classmethod
    def strip_and_reject_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Value must not be blank")
        return value

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, value: str) -> str:
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", value):
            raise ValueError(
                "Slug must contain lowercase letters, numbers, "
                "and single hyphens between words"
            )
        return value


class CategoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    slug: str
    parent_id: UUID | None
    created_at: datetime
