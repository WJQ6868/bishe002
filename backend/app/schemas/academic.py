from pydantic import BaseModel


class CollegeOut(BaseModel):
    id: int
    name: str
    code: str
    status: int

    class Config:
        from_attributes = True


class MajorOut(BaseModel):
    id: int
    name: str
    code: str | None
    status: int
    college_id: int | None

    class Config:
        from_attributes = True


class ClassOut(BaseModel):
    id: int
    name: str
    code: str | None = None
    status: int = 1
    major_id: int | None = None
    major_name: str | None = None
    teacher_id: str | None = None
    teacher_name: str | None = None
    student_count: int

    class Config:
        from_attributes = True


class StudentOut(BaseModel):
    id: int
    student_code: str
    name: str
    gender: int | None = None
    mobile: str | None = None
    status: int = 1
    class_id: int | None = None
    class_name: str | None = None

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
