from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CourseCreate(BaseModel):
    code: str = Field(min_length=1, max_length=30)
    name: str = Field(min_length=1, max_length=150)
    school_id: int = Field(gt=0)
    duration_years: int = Field(gt=0)
    total_semesters: int = Field(gt=0)
    is_active: bool = True


class CourseUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=30)
    name: str | None = Field(default=None, min_length=1, max_length=150)
    school_id: int | None = Field(default=None, gt=0)
    duration_years: int | None = Field(default=None, gt=0)
    total_semesters: int | None = Field(default=None, gt=0)
    is_active: bool | None = None


class CourseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    code: str
    name: str
    school_id: int
    duration_years: int
    total_semesters: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
