from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..dependencies.auth import get_current_user
from ..models.course import Course
from ..models.student import CourseSelection, Grade, Student
from ..models.admin_user import StudentUser, ClassRoom


router = APIRouter(prefix="/teacher/grades", tags=["Teacher Grades"])


class CourseOut(BaseModel):
    id: int
    name: str
    course_type: Optional[str] = None


class GradeEntry(BaseModel):
    student_id: str = Field(..., description="学号")
    midterm_score: Optional[float] = None
    final_score: Optional[float] = None


class GradeSaveRequest(BaseModel):
    course_id: int
    items: List[GradeEntry]


def _ensure_teacher_or_admin(user):
    if user.role not in ("teacher", "admin"):
        raise HTTPException(status_code=403, detail="Only teachers or admins can access")


async def _ensure_course_access(db: AsyncSession, course_id: int, user) -> Course:
    res = await db.execute(select(Course).where(Course.id == course_id))
    course = res.scalars().first()
    if not course:
        raise HTTPException(status_code=404, detail="课程不存在")
    if user.role == "teacher" and str(course.teacher_id) != str(user.username):
        raise HTTPException(status_code=403, detail="无权限访问该课程")
    return course


@router.get("/courses")
async def list_teacher_courses(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _ensure_teacher_or_admin(current_user)
    if current_user.role == "teacher":
        stmt = select(Course).where(Course.teacher_id == str(current_user.username))
    else:
        stmt = select(Course)
    courses = (await db.execute(stmt.order_by(Course.id))).scalars().all()
    return {"items": [CourseOut(id=c.id, name=c.name, course_type=c.course_type) for c in courses]}


@router.get("/students")
async def list_course_students(
    course_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _ensure_teacher_or_admin(current_user)
    await _ensure_course_access(db, course_id, current_user)

    res = await db.execute(select(CourseSelection.student_id).where(CourseSelection.course_id == course_id))
    enrolled_ids = [str(x) for x in res.scalars().all() if x]

    students_payload: List[dict] = []
    student_ids: List[str] = []

    if enrolled_ids:
        stmt = (
            select(StudentUser, ClassRoom)
            .join(ClassRoom, ClassRoom.id == StudentUser.class_id, isouter=True)
            .where(StudentUser.student_no.in_(enrolled_ids))
            .order_by(StudentUser.student_no)
        )
        rows = (await db.execute(stmt)).all()
        for stu, clazz in rows:
            students_payload.append(
                {
                    "student_id": stu.student_no,
                    "name": stu.name,
                    "class_name": clazz.name if clazz else "",
                }
            )
            student_ids.append(stu.student_no)

        missing_ids = [sid for sid in enrolled_ids if sid not in set(student_ids)]
        if missing_ids:
            legacy_rows = (await db.execute(select(Student).where(Student.id.in_(missing_ids)))).scalars().all()
            for stu in legacy_rows:
                students_payload.append(
                    {
                        "student_id": stu.id,
                        "name": stu.name,
                        "class_name": "",
                    }
                )
                student_ids.append(stu.id)
    if not enrolled_ids or not students_payload:
        stmt = (
            select(StudentUser, ClassRoom)
            .join(ClassRoom, ClassRoom.id == StudentUser.class_id, isouter=True)
            .order_by(StudentUser.student_no)
        )
        rows = (await db.execute(stmt)).all()
        for stu, clazz in rows:
            students_payload.append(
                {
                    "student_id": stu.student_no,
                    "name": stu.name,
                    "class_name": clazz.name if clazz else "",
                }
            )
            student_ids.append(stu.student_no)

    grade_map: dict[tuple[str, str], float] = {}
    if student_ids:
        grade_rows = (
            await db.execute(
                select(Grade)
                .where(Grade.course_id == course_id)
                .where(Grade.student_id.in_(student_ids))
            )
        ).scalars().all()
        for g in grade_rows:
            grade_map[(g.student_id, g.exam_type)] = g.score

    for item in students_payload:
        sid = item["student_id"]
        item["midterm_score"] = grade_map.get((sid, "midterm"))
        item["final_score"] = grade_map.get((sid, "final"))

    return {"items": students_payload}


@router.post("/save")
async def save_grades(
    payload: GradeSaveRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _ensure_teacher_or_admin(current_user)
    await _ensure_course_access(db, payload.course_id, current_user)

    saved = 0
    for entry in payload.items:
        if entry.midterm_score is not None:
            stmt = select(Grade).where(
                Grade.student_id == entry.student_id,
                Grade.course_id == payload.course_id,
                Grade.exam_type == "midterm",
            )
            res = await db.execute(stmt)
            grade = res.scalars().first()
            if grade:
                grade.score = entry.midterm_score
            else:
                grade = Grade(
                    student_id=entry.student_id,
                    course_id=payload.course_id,
                    score=entry.midterm_score,
                    exam_type="midterm",
                )
                db.add(grade)
            saved += 1
        if entry.final_score is not None:
            stmt = select(Grade).where(
                Grade.student_id == entry.student_id,
                Grade.course_id == payload.course_id,
                Grade.exam_type == "final",
            )
            res = await db.execute(stmt)
            grade = res.scalars().first()
            if grade:
                grade.score = entry.final_score
            else:
                grade = Grade(
                    student_id=entry.student_id,
                    course_id=payload.course_id,
                    score=entry.final_score,
                    exam_type="final",
                )
                db.add(grade)
            saved += 1

        # Ensure legacy students table is synced for analysis
        legacy = await db.execute(select(Student).where(Student.id == entry.student_id))
        if not legacy.scalars().first():
            stu_res = await db.execute(select(StudentUser).where(StudentUser.student_no == entry.student_id))
            stu = stu_res.scalars().first()
            if stu:
                db.add(
                    Student(
                        id=stu.student_no,
                        name=stu.name,
                        major=stu.major or None,
                        grade=str(stu.grade_id) if stu.grade_id else None,
                    )
                )

    await db.commit()
    return {"saved": saved}
