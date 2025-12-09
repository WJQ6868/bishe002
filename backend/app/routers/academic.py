from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models.academic import (
    AcademicClass,
    AcademicCourse,
    AcademicCourseTeacher,
    AcademicMajor,
    AcademicStudent,
)
from ..models.course import Teacher
from ..schemas.academic import (
    ClassOut,
    CourseOut,
    CourseTeacherOut,
    MajorOut,
    StudentOut,
)

router = APIRouter(tags=["Academic Hierarchy"])


@router.get("/major/list")
async def list_majors(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AcademicMajor).order_by(AcademicMajor.id))
    majors = result.scalars().all()
    return {"items": [MajorOut.model_validate(m) for m in majors]}


@router.get("/major/class/list")
async def list_classes(
    major_id: int = Query(..., description="Major ID"),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AcademicClass)
        .where(AcademicClass.major_id == major_id)
        .order_by(AcademicClass.id)
    )
    classes = result.scalars().all()
    return {"items": [ClassOut.model_validate(c) for c in classes]}


@router.get("/class/student/list")
async def list_students(
    class_id: int = Query(..., description="Class ID"),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AcademicStudent)
        .where(AcademicStudent.class_id == class_id)
        .order_by(AcademicStudent.id)
    )
    students = result.scalars().all()
    return {"items": [StudentOut.model_validate(s) for s in students]}


@router.get("/major/course/list")
async def list_courses(
    major_id: int = Query(..., description="Major ID"),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AcademicCourse)
        .where(AcademicCourse.major_id == major_id)
        .order_by(AcademicCourse.id)
    )
    courses = result.scalars().all()
    return {"items": [CourseOut.model_validate(c) for c in courses]}


@router.get("/course/teacher/list")
async def list_course_teachers(
    course_id: int = Query(..., description="Course ID"),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AcademicCourseTeacher, Teacher)
        .join(Teacher, Teacher.id == AcademicCourseTeacher.teacher_id, isouter=True)
        .where(AcademicCourseTeacher.course_id == course_id)
    )
    rows = result.all()
    items = []
    for link, teacher in rows:
        name = teacher.name if teacher else f"教师 {link.teacher_id}"
        items.append(CourseTeacherOut(teacher_id=link.teacher_id, name=name))
    return {"items": items}
