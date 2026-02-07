from datetime import date, datetime, time, timedelta

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete, select
from ..schemas.schedule import (
    ScheduleRequest,
    ScheduleResponse,
    ScheduleSaveRequest,
)
from ..algorithms.schedule_genetic import GeneticSchedule
from ..database import get_db
from ..dependencies.auth import get_current_admin
from ..models.schedule import Classroom, Schedule
from ..models.course import Course, Teacher
from ..models.teaching import WorkSchedule, WorkType
from ..models.user import User
import time as pytime

router = APIRouter(prefix="/schedule", tags=["Schedule Management"])

_SYNC_REMARK_PREFIX = "[排课同步]"
_PERIOD_STARTS = {
    0: time(8, 0),
    1: time(10, 0),
    2: time(14, 0),
    3: time(16, 0),
    4: time(19, 0),
    5: time(20, 40),
}


def _current_week_monday(today: date | None = None) -> date:
    base = today or date.today()
    return base - timedelta(days=base.weekday())


async def _resolve_teacher_user_id(db: AsyncSession, teacher_id: str) -> int | None:
    tid = str(teacher_id or "").strip()
    if not tid:
        return None
    user = (await db.execute(select(User).where(User.username == tid))).scalars().first()
    if user:
        return int(user.id)
    if tid.isdigit():
        user = (await db.execute(select(User).where(User.id == int(tid)))).scalars().first()
        if user:
            return int(user.id)
    return None


def _resolve_period_time(period: int) -> time:
    return _PERIOD_STARTS.get(period, time(8, 0))

@router.post("/generate", response_model=ScheduleResponse)
async def generate_schedule(
    request: ScheduleRequest,
    current_user=Depends(get_current_admin),
):
    start_time = pytime.time()
    
    ga = GeneticSchedule(request.teachers, request.courses, request.classrooms)
    best_schedule, stats = ga.evolve()
    
    if best_schedule is None:
        raise HTTPException(status_code=500, detail="Failed to generate schedule")
    
    formatted_schedule = ga.format_result(best_schedule)
    entries = ga.schedule_to_entries(best_schedule)
    
    end_time = pytime.time()
    print(f"Scheduling took {end_time - start_time:.2f} seconds")
    
    return ScheduleResponse(
        schedule=formatted_schedule,
        fitness=stats["fitness"],
        utilization=stats["utilization"],
        conflict_rate=stats["conflicts"],
        entries=entries,
    )


@router.post("/save")
async def save_schedule(
    payload: ScheduleSaveRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_admin),
):
    if payload.clear_existing:
        await db.execute(delete(Schedule))
        await db.execute(delete(WorkSchedule).where(WorkSchedule.remark.like(f"{_SYNC_REMARK_PREFIX}%")))

    course_ids = {int(entry.course_id) for entry in payload.entries}
    classroom_ids = {int(entry.classroom_id) for entry in payload.entries}

    courses = {}
    classrooms = {}
    teachers = {}
    if course_ids:
        res = await db.execute(select(Course).where(Course.id.in_(course_ids)))
        courses = {int(c.id): c for c in res.scalars().all()}
        teacher_ids = {str(c.teacher_id) for c in courses.values()}
        if teacher_ids:
            res = await db.execute(select(Teacher).where(Teacher.id.in_(teacher_ids)))
            teachers = {str(t.id): t for t in res.scalars().all()}
    if classroom_ids:
        res = await db.execute(select(Classroom).where(Classroom.id.in_(classroom_ids)))
        classrooms = {int(c.id): c for c in res.scalars().all()}

    monday = _current_week_monday()

    for entry in payload.entries:
        schedule_row = Schedule(
            course_id=entry.course_id,
            classroom_id=entry.classroom_id,
            teacher_id=entry.teacher_id,
            day=entry.day,
            period=entry.period,
        )
        db.add(schedule_row)

        course = courses.get(int(entry.course_id))
        classroom = classrooms.get(int(entry.classroom_id))
        teacher_name = teachers.get(str(entry.teacher_id)).name if teachers.get(str(entry.teacher_id)) else f"教师{entry.teacher_id}"
        course_name = course.name if course else f"课程{entry.course_id}"
        classroom_name = classroom.name if classroom else f"教室{entry.classroom_id}"

        user_id = await _resolve_teacher_user_id(db, str(entry.teacher_id))
        if user_id is not None:
            class_date = monday + timedelta(days=int(entry.day))
            period_time = _resolve_period_time(int(entry.period))
            schedule_time = datetime.combine(class_date, period_time)
            db.add(
                WorkSchedule(
                    teacher_id=user_id,
                    time=schedule_time,
                    content=f"{course_name}（{classroom_name}）",
                    type=WorkType.CLASS.value,
                    remark=f"{_SYNC_REMARK_PREFIX}班级/教室:{classroom_name} 教师:{teacher_name}",
                )
            )

    await db.commit()
    return {"message": "Schedule saved", "count": len(payload.entries)}
