from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.db.models.faculty import FacultyDesignation


class FacultyCreate(BaseModel):
    employee_id: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=150)
    email: EmailStr
    designation: FacultyDesignation
    school_id: int = Field(gt=0)
    is_active: bool = True


class FacultyUpdate(BaseModel):
    employee_id: str | None = Field(default=None, min_length=1, max_length=50)
    name: str | None = Field(default=None, min_length=1, max_length=150)
    email: EmailStr | None = None
    designation: FacultyDesignation | None = None
    school_id: int | None = Field(default=None, gt=0)
    is_active: bool | None = None


class FacultyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    employee_id: str
    name: str
    email: EmailStr
    designation: FacultyDesignation
    school_id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
