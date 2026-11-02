from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.db.models.scheduling_rules import ResourceType, Weekday


class UnavailabilityCreate(BaseModel):
    resource_type: ResourceType
    resource_id: int = Field(gt=0)
    day: Weekday
    start_period: int = Field(ge=1)
    end_period: int = Field(ge=1)
    reason: str | None = Field(default=None, max_length=255)

    @model_validator(mode="after")
    def _check_range(self):
        if self.end_period < self.start_period:
            raise ValueError("end_period must be greater than or equal to start_period")
        return self


class UnavailabilityUpdate(BaseModel):
    day: Weekday | None = None
    start_period: int | None = Field(default=None, ge=1)
    end_period: int | None = Field(default=None, ge=1)
    reason: str | None = Field(default=None, max_length=255)


class UnavailabilityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    resource_type: ResourceType
    resource_id: int
    day: Weekday
    start_period: int
    end_period: int
    reason: str | None
    created_at: datetime
    updated_at: datetime


class GroupBlockedSlotCreate(BaseModel):
    academic_group_id: int = Field(gt=0)
    day: Weekday
    period: int = Field(ge=1)
    label: str | None = Field(default=None, max_length=100)


class GroupBlockedSlotUpdate(BaseModel):
    day: Weekday | None = None
    period: int | None = Field(default=None, ge=1)
    label: str | None = Field(default=None, max_length=100)


class GroupBlockedSlotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    academic_group_id: int
    day: Weekday
    period: int
    label: str | None
    created_at: datetime
    updated_at: datetime


class SessionLockCreate(BaseModel):
    teaching_assignment_id: int = Field(gt=0)
    session_number: int = Field(ge=1)
    day: Weekday
    start_period: int = Field(ge=1)
    room_id: int | None = Field(default=None, gt=0)


class SessionLockUpdate(BaseModel):
    day: Weekday | None = None
    start_period: int | None = Field(default=None, ge=1)
    room_id: int | None = Field(default=None, gt=0)


class SessionLockResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    teaching_assignment_id: int
    session_number: int
    day: Weekday
    start_period: int
    room_id: int | None
    created_at: datetime
    updated_at: datetime
