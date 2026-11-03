from fastapi import APIRouter, Depends

from app.api.v1 import (
    assignments,
    auth,
    courses,
    data_io,
    faculty,
    groups,
    rooms,
    scheduling_rules,
    schools,
    subjects,
    timetable,
    users,
)

api_router = APIRouter(prefix="/api/v1")

# Public (login) and per-route checks (users: admin; timetable: see module).
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(timetable.router)

# Scheduling data: administrators and coordinators only.
staff = [Depends(auth.require_staff)]
for module_router in (
    schools.router,
    courses.router,
    faculty.router,
    rooms.router,
    subjects.router,
    groups.router,
    assignments.router,
    scheduling_rules.unavailability_router,
    scheduling_rules.group_blocks_router,
    scheduling_rules.session_locks_router,
    data_io.router,
):
    api_router.include_router(module_router, dependencies=staff)
