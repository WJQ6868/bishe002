from pydantic import BaseModel


class StatsResponse(BaseModel):
    total_courses: int
    total_students: int
    total_teachers: int
    available_classrooms: int


class StatsSeedRequest(BaseModel):
    total_courses: int = 120
    total_students: int = 3500
    total_teachers: int = 85
    available_classrooms: int = 40
