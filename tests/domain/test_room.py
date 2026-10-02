import pytest

from app.domain.room import RoomType, SchedulingRoom


def test_scheduling_room_accepts_valid_values():
    room = SchedulingRoom(
        id=1,
        room_type=RoomType.LECTURE_HALL,
        capacity=60,
        is_shared=True,
    )

    assert room.id == 1
    assert room.room_type == RoomType.LECTURE_HALL
    assert room.capacity == 60
    assert room.is_shared is True


def test_scheduling_room_defaults_to_not_shared():
    room = SchedulingRoom(
        id=1,
        room_type=RoomType.CLASSROOM,
        capacity=40,
    )

    assert room.is_shared is False


@pytest.mark.parametrize("room_id", [0, -1])
def test_scheduling_room_rejects_invalid_id(room_id):
    with pytest.raises(ValueError, match="id must be greater than 0"):
        SchedulingRoom(
            id=room_id,
            room_type=RoomType.CLASSROOM,
            capacity=40,
        )


@pytest.mark.parametrize("capacity", [0, -1])
def test_scheduling_room_rejects_invalid_capacity(capacity):
    with pytest.raises(ValueError, match="capacity must be greater than 0"):
        SchedulingRoom(
            id=1,
            room_type=RoomType.CLASSROOM,
            capacity=capacity,
        )