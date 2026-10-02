from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.db.models.teaching_assignment import AssignmentMode


class TeachingAssignmentCreate(BaseModel):
    subject_id: int = Field(gt=0)
    course_id: int = Field(gt=0)
    academic_group_id: int = Field(gt=0)
    faculty_id: int = Field(gt=0)
    sessions_per_week: int = Field(gt=0)
    duration_periods: int = Field(gt=0)
    mode: AssignmentMode
    required_room_type: str | None = Field(default=None, max_length=50)
    is_active: bool = True


class TeachingAssignmentUpdate(BaseModel):
    subject_id: int | None = Field(default=None, gt=0)
    course_id: int | None = Field(default=None, gt=0)
    academic_group_id: int | None = Field(default=None, gt=0)
    faculty_id: int | None = Field(default=None, gt=0)
    sessions_per_week: int | None = Field(default=None, gt=0)
    duration_periods: int | None = Field(default=None, gt=0)
    mode: AssignmentMode | None = None
    required_room_type: str | None = Field(default=None, max_length=50)
    is_active: bool | None = None


class TeachingAssignmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    subject_id: int
    course_id: int
    academic_group_id: int
    faculty_id: int
    sessions_per_week: int
    duration_periods: int
    mode: AssignmentMode
    required_room_type: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
