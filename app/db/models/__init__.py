from app.db.models.academic_group import AcademicGroup, GroupType
from app.db.models.course import Course
from app.db.models.faculty import Faculty, FacultyDesignation
from app.db.models.room import Room, RoomType
from app.db.models.school import School
from app.db.models.subject import Subject, SubjectType
from app.db.models.teaching_assignment import AssignmentMode, TeachingAssignment

__all__ = [
    "AcademicGroup",
    "GroupType",
    "Course",
    "Faculty",
    "FacultyDesignation",
    "Room",
    "RoomType",
    "School",
    "Subject",
    "SubjectType",
    "AssignmentMode",
    "TeachingAssignment",
]
