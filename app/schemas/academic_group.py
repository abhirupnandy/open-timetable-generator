from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.db.models.academic_group import GroupType


class AcademicGroupCreate(BaseModel):
    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=150)
    group_type: GroupType
    course_id: int = Field(gt=0)
    parent_group_id: int | None = Field(default=None, gt=0)
    capacity: int | None = Field(default=None, gt=0)
    is_active: bool = True


class AcademicGroupUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=50)
    name: str | None = Field(default=None, min_length=1, max_length=150)
    group_type: GroupType | None = None
    course_id: int | None = Field(default=None, gt=0)
    parent_group_id: int | None = Field(default=None, gt=0)
    capacity: int | None = Field(default=None, gt=0)
    is_active: bool | None = None


class AcademicGroupResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    code: str
    name: str
    group_type: GroupType
    course_id: int
    parent_group_id: int | None
    capacity: int | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
