from pydantic import BaseModel


class MajorOut(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True


class ClassOut(BaseModel):
    id: int
    name: str
    student_count: int

    class Config:
        from_attributes = True


class StudentOut(BaseModel):
    id: int
    student_code: str
    name: str

    class Config:
        from_attributes = True


class CourseOut(BaseModel):
    id: int
    name: str
    credit: float
    class_hours: int

    class Config:
        from_attributes = True


class CourseTeacherOut(BaseModel):
    teacher_id: str
    name: str
