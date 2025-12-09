from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime

class CourseBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=50, description="课程名称")
    credit: int = Field(..., ge=1, le=5, description="学分 (1-5)")
    teacher_id: str = Field(..., description="教师ID")
    capacity: int = Field(..., ge=20, description="课程容量 (>=20)")
    course_type: str = Field(..., description="课程类型 (必修/选修)")

    @field_validator("teacher_id", mode="before")
    @classmethod
    def normalize_teacher_id(cls, value):
        if value is None:
            raise ValueError("teacher_id is required")
        return str(value)

class CourseCreate(CourseBase):
    pass

class CourseUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=50)
    credit: Optional[int] = Field(None, ge=1, le=5)
    teacher_id: Optional[str] = None
    capacity: Optional[int] = Field(None, ge=20)
    course_type: Optional[str] = None

    @field_validator("teacher_id", mode="before")
    @classmethod
    def normalize_optional_teacher_id(cls, value):
        if value is None:
            return value
        return str(value)

class CourseResponse(CourseBase):
    id: int
    create_time: datetime

    class Config:
        orm_mode = True


class TeacherOptionOut(BaseModel):
    id: str
    name: str
