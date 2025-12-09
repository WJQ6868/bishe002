from pydantic import BaseModel, Field
from typing import List, Dict, Any


class TeacherItem(BaseModel):
    id: str
    name: str


class CourseItem(BaseModel):
    id: int
    name: str
    teacher_id: str
    is_required: bool = Field(False, description="是否必修课程")


class ClassroomItem(BaseModel):
    id: int
    name: str
    capacity: int
    is_multimedia: bool = Field(False, description="是否多媒体教室")


class ScheduleRequest(BaseModel):
    teachers: List[TeacherItem]
    courses: List[CourseItem]
    classrooms: List[ClassroomItem]


class ScheduleEntry(BaseModel):
    course_id: int
    teacher_id: str
    classroom_id: int
    day: int
    period: int


class ScheduleResponse(BaseModel):
    schedule: Dict[str, Any] = Field(..., description="排课结果，包含教师视角和教室视角")
    fitness: float
    utilization: float
    conflict_rate: float
    entries: List[ScheduleEntry]


class ScheduleSaveRequest(BaseModel):
    entries: List[ScheduleEntry]
    clear_existing: bool = True
