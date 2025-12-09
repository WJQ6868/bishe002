from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete
from ..schemas.schedule import (
    ScheduleRequest,
    ScheduleResponse,
    ScheduleSaveRequest,
)
from ..algorithms.schedule_genetic import GeneticSchedule
from ..database import get_db
from ..dependencies.auth import get_current_admin
from ..models.schedule import Schedule
import time

router = APIRouter(prefix="/schedule", tags=["Schedule Management"])

@router.post("/generate", response_model=ScheduleResponse)
async def generate_schedule(
    request: ScheduleRequest,
    current_user=Depends(get_current_admin),
):
    start_time = time.time()
    
    ga = GeneticSchedule(request.teachers, request.courses, request.classrooms)
    best_schedule, stats = ga.evolve()
    
    if best_schedule is None:
        raise HTTPException(status_code=500, detail="Failed to generate schedule")
    
    formatted_schedule = ga.format_result(best_schedule)
    entries = ga.schedule_to_entries(best_schedule)
    
    end_time = time.time()
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

    for entry in payload.entries:
        schedule_row = Schedule(
            course_id=entry.course_id,
            classroom_id=entry.classroom_id,
            teacher_id=entry.teacher_id,
            day=entry.day,
            period=entry.period,
        )
        db.add(schedule_row)

    await db.commit()
    return {"message": "Schedule saved", "count": len(payload.entries)}
