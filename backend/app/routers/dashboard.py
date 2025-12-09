import json
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional

from ..database import get_db
from ..models.course import Course, Teacher
from ..models.student import Student
from ..models.user import User
from ..models.schedule import Classroom, ClassroomResource
from ..schemas.dashboard import StatsResponse, StatsSeedRequest
from ..dependencies.auth import get_current_admin


router = APIRouter(prefix="/dashboard", tags=["仪表盘"])


@router.get("/stats", response_model=StatsResponse)
async def get_stats(db: AsyncSession = Depends(get_db)):
    c_res = await db.execute(select(func.count(Course.id)))
    # 为了与“用户管理”页面一致，学生与教师统计改为 sys_users 角色计数
    s_res = await db.execute(select(func.count(User.id)).where(User.role == "student"))
    t_res = await db.execute(select(func.count(User.id)).where(User.role == "teacher"))
    r_res = await db.execute(select(func.count(Classroom.id)))
    return StatsResponse(
        total_courses=int((c_res.scalar() or 0)),
        total_students=int((s_res.scalar() or 0)),
        total_teachers=int((t_res.scalar() or 0)),
        available_classrooms=int((r_res.scalar() or 0)),
    )


@router.post("/seed", response_model=StatsResponse)
async def seed_stats(
    request: StatsSeedRequest,
    db: AsyncSession = Depends(get_db),
    admin: dict = Depends(get_current_admin),
):
    t_count = int((await db.execute(select(func.count(Teacher.id)))).scalar() or 0)
    if t_count < request.total_teachers:
        db.add_all([Teacher(name=f"教师{i}") for i in range(t_count + 1, request.total_teachers + 1)])
        await db.commit()

    teacher_ids = (await db.execute(select(Teacher.id))).scalars().all()

    c_count = int((await db.execute(select(func.count(Course.id)))).scalar() or 0)
    if c_count < request.total_courses and teacher_ids:
        import itertools

        cycle_ids = itertools.cycle(teacher_ids)
        courses = []
        for i in range(c_count + 1, request.total_courses + 1):
            tid = next(cycle_ids)
            courses.append(
                Course(name=f"课程{i}", credit=3, teacher_id=tid, capacity=60, course_type="必修")
            )
        db.add_all(courses)
        await db.commit()

    s_count = int((await db.execute(select(func.count(Student.id)))).scalar() or 0)
    if s_count < request.total_students:
        batch = []
        for i in range(s_count + 1, request.total_students + 1):
            sid = f"S{i:05d}"
            batch.append(Student(id=sid, name=f"学生{i}", major="计算机", grade="2023"))
            if len(batch) % 500 == 0:
                db.add_all(batch)
                await db.commit()
                batch = []
        if batch:
            db.add_all(batch)
            await db.commit()

    r_count = int((await db.execute(select(func.count(Classroom.id)))).scalar() or 0)
    if r_count < request.available_classrooms:
        for i in range(r_count + 1, request.available_classrooms + 1):
            classroom = Classroom(name=f"教室-{100 + i}", capacity=60, is_multimedia=(i % 2 == 0))
            db.add(classroom)
            await db.flush()
            db.add(
                ClassroomResource(
                    classroom_id=classroom.id,
                    code=f"CLS-{classroom.id:04d}",
                    location=f"教学楼{i % 4 + 1}层",
                    devices=json.dumps(["多媒体"]) if classroom.is_multimedia else None,
                    status="idle",
                )
            )
        await db.commit()

    c_res = await db.execute(select(func.count(Course.id)))
    s_res = await db.execute(select(func.count(Student.id)))
    t_res = await db.execute(select(func.count(Teacher.id)))
    r_res = await db.execute(select(func.count(Classroom.id)))
    return StatsResponse(
        total_courses=int(c_res.scalar() or 0),
        total_students=int(s_res.scalar() or 0),
        total_teachers=int(t_res.scalar() or 0),
        available_classrooms=int(r_res.scalar() or 0),
    )
