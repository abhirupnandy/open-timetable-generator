from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class SchoolCreate(BaseModel):
    code: str = Field(min_length=1, max_length=20)
    name: str = Field(min_length=1, max_length=150)
    is_active: bool = True


class SchoolUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=20)
    name: str | None = Field(default=None, min_length=1, max_length=150)
    is_active: bool | None = None


class SchoolResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    code: str
    name: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
