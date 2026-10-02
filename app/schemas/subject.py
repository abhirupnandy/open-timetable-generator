from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.db.models.subject import SubjectType


class SubjectCreate(BaseModel):
    code: str = Field(min_length=1, max_length=30)
    name: str = Field(min_length=1, max_length=150)
    subject_type: SubjectType
    is_active: bool = True


class SubjectUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=30)
    name: str | None = Field(default=None, min_length=1, max_length=150)
    subject_type: SubjectType | None = None
    is_active: bool | None = None


class SubjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    code: str
    name: str
    subject_type: SubjectType
    is_active: bool
    created_at: datetime
    updated_at: datetime
