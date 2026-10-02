from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.db.models.room import RoomType


class RoomCreate(BaseModel):
    code: str = Field(min_length=1, max_length=30)
    name: str = Field(min_length=1, max_length=150)
    room_type: RoomType
    capacity: int = Field(gt=0)
    school_id: int = Field(gt=0)
    is_shared: bool = False
    is_active: bool = True


class RoomUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=30)
    name: str | None = Field(default=None, min_length=1, max_length=150)
    room_type: RoomType | None = None
    capacity: int | None = Field(default=None, gt=0)
    school_id: int | None = Field(default=None, gt=0)
    is_shared: bool | None = None
    is_active: bool | None = None


class RoomResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    code: str
    name: str
    room_type: RoomType
    capacity: int
    school_id: int
    is_shared: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime
