"""
教师教学管理 - 工作安排与调课 API
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, desc
from typing import List, Optional
from datetime import datetime

from ..database import get_db
from ..models.teaching import ClassAdjust, WorkSchedule, AdjustStatus, WorkType
from ..models.course import Course
from ..models.user import User, UserProfile
from ..schemas.teaching import (
    ClassAdjustCreate,
    ClassAdjustResponse,
    ClassAdjustAdminItem,
    WorkScheduleCreate,
    WorkScheduleResponse,
)
from ..dependencies.auth import get_current_user, get_current_admin

router = APIRouter(prefix="/work", tags=["工作安排"])


@router.post("/adjust/apply", response_model=ClassAdjustResponse)
async def apply_adjust(
    data: ClassAdjustCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    提交调课申请
    """
    if current_user.role != "teacher":
        raise HTTPException(status_code=403, detail="Only teachers can apply")
        
    new_adjust = ClassAdjust(
        teacher_id=current_user.id,
        course_id=data.course_id,
        old_time=data.old_time,
        new_time=data.new_time,
        old_classroom=data.old_classroom,
        new_classroom=data.new_classroom,
        reason=data.reason,
        file_url=data.file_url,
        status=AdjustStatus.PENDING.value
    )
    
    db.add(new_adjust)
    await db.commit()
    await db.refresh(new_adjust)
    
    return ClassAdjustResponse.model_validate(new_adjust)


@router.get("/schedule", response_model=List[WorkScheduleResponse])
async def get_schedule(
    start: Optional[str] = None, # YYYY-MM-DD
    end: Optional[str] = None,   # YYYY-MM-DD
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取工作安排
    """
    if current_user.role != "teacher":
        raise HTTPException(status_code=403, detail="Only teachers can access")
        
    query = select(WorkSchedule).where(WorkSchedule.teacher_id == current_user.id)
    
    if start and end:
        try:
            start_date = datetime.strptime(start, "%Y-%m-%d")
            end_date = datetime.strptime(end, "%Y-%m-%d")
            query = query.where(
                and_(
                    WorkSchedule.time >= start_date,
                    WorkSchedule.time <= end_date
                )
            )
        except ValueError:
            pass
            
    query = query.order_by(WorkSchedule.time)
    
    result = await db.execute(query)
    schedules = result.scalars().all()
    
    return [WorkScheduleResponse.model_validate(s) for s in schedules]


@router.post("/adjust/approve")
async def approve_adjust(
    adjust_id: int,
    result: str, # approved/rejected
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    管理员审批调课申请
    """
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can approve")
        
    stmt = select(ClassAdjust).where(ClassAdjust.id == adjust_id)
    result_db = await db.execute(stmt)
    adjust = result_db.scalars().first()
    
    if not adjust:
        raise HTTPException(status_code=404, detail="Adjustment not found")
        
    if adjust.status != AdjustStatus.PENDING.value:
        raise HTTPException(status_code=400, detail="Adjustment is not pending")
        
    if result not in [AdjustStatus.APPROVED.value, AdjustStatus.REJECTED.value]:
         # 兼容前端传参可能是 "approved"/"rejected" 或者是中文枚举值
         # 这里简单处理，假设前端传的是 "approved" 或 "rejected"，映射到枚举
         if result == "approved":
             adjust.status = AdjustStatus.APPROVED.value
         elif result == "rejected":
             adjust.status = AdjustStatus.REJECTED.value
         else:
             # 直接尝试赋值，如果前端传的是中文
             adjust.status = result

    await db.commit()
    
    return {"message": "Approval success"}


@router.get("/adjust/list", response_model=List[ClassAdjustAdminItem])
async def list_adjust_records(
    status: Optional[str] = Query(None, description="寰呭鏍?/宸查€氳繃/宸叉嫆缁?"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    query = (
        select(
            ClassAdjust,
            Course.name.label("course_name"),
            User.username.label("teacher_account"),
            UserProfile.name.label("teacher_name"),
        )
        .join(Course, Course.id == ClassAdjust.course_id, isouter=True)
        .join(User, User.id == ClassAdjust.teacher_id, isouter=True)
        .join(UserProfile, UserProfile.user_id == User.id, isouter=True)
        .order_by(ClassAdjust.create_time.desc())
    )
    if status:
        query = query.where(ClassAdjust.status == status)

    result = await db.execute(query)
    rows = result.all()

    items: List[ClassAdjustAdminItem] = []
    for adjust, course_name, teacher_account, teacher_name in rows:
        items.append(
            ClassAdjustAdminItem(
                id=adjust.id,
                teacher_id=adjust.teacher_id,
                teacher_name=teacher_name or teacher_account or f"教师{adjust.teacher_id}",
                course_id=adjust.course_id,
                course_name=course_name or f"课程{adjust.course_id}",
                old_time=adjust.old_time,
                new_time=adjust.new_time,
                old_classroom=adjust.old_classroom,
                new_classroom=adjust.new_classroom,
                reason=adjust.reason,
                status=adjust.status,
                create_time=adjust.create_time,
            )
        )
    return items
