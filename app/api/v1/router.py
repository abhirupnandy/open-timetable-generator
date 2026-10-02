from fastapi import APIRouter

from app.api.v1 import assignments, courses, faculty, groups, rooms, schools, subjects

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(schools.router)
api_router.include_router(courses.router)
api_router.include_router(faculty.router)
api_router.include_router(rooms.router)
api_router.include_router(subjects.router)
api_router.include_router(groups.router)
api_router.include_router(assignments.router)
