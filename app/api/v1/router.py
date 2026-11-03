from fastapi import APIRouter

from app.api.v1 import (
    assignments,
    courses,
    data_io,
    faculty,
    groups,
    rooms,
    scheduling_rules,
    schools,
    subjects,
    timetable,
)

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(schools.router)
api_router.include_router(courses.router)
api_router.include_router(faculty.router)
api_router.include_router(rooms.router)
api_router.include_router(subjects.router)
api_router.include_router(groups.router)
api_router.include_router(assignments.router)
api_router.include_router(scheduling_rules.unavailability_router)
api_router.include_router(scheduling_rules.group_blocks_router)
api_router.include_router(scheduling_rules.session_locks_router)
api_router.include_router(timetable.router)
api_router.include_router(data_io.router)
