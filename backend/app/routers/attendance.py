"""
教师教学管理 - 点名 API
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, desc
from typing import List, Optional
from datetime import datetime, timedelta
import uuid
import random

from ..database import get_db
from ..models.teaching import Attendance, AttendanceStatus
from ..models.course import Course
from ..models.student import Student, CourseSelection
from ..models.user import User
from ..schemas.teaching import AttendanceCreate, AttendanceSign, AttendanceUpdate, AttendanceResponse
from ..dependencies.auth import get_current_user
from ..services.socket_manager import sio

router = APIRouter(prefix="/attendance", tags=["上课点名"])

# 内存存储签到码: {code: {course_id, expire_time}}
active_codes = {}


@router.post("/create")
async def create_attendance_code(
    data: AttendanceCreate,
    current_user: User = Depends(get_current_user)
):
    """
    生成签到二维码
    """
    if current_user.role != "teacher":
        raise HTTPException(status_code=403, detail="Only teachers can create attendance")
        
    # 生成 6 位数字签到码（唯一，避免与现存未过期码冲突）
    while True:
        code = ''.join(random.choices('0123456789', k=6))
        if code not in active_codes:
            break
    expire_time = datetime.now() + timedelta(minutes=data.duration)
    
    active_codes[code] = {
        "course_id": data.course_id,
        "teacher_id": current_user.id,
        "expire_time": expire_time
    }
    
    return {"code": code, "expire_time": expire_time}


@router.post("/sign")
async def sign_attendance(
    data: AttendanceSign,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    学生扫码签到
    """
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="Only students can sign in")
        
    # 校验签到码
    info = active_codes.get(data.code)
    if not info:
        raise HTTPException(status_code=400, detail="Invalid code")
        
    if datetime.now() > info["expire_time"]:
        raise HTTPException(status_code=400, detail="Code expired")
        
    course_id = info["course_id"]
    
    # 校验是否已签到
    # 注意：这里需要判断是否是"本次"点名
    # 简单逻辑：查找该课程该学生最近 1 小时内的签到记录
    one_hour_ago = datetime.now() - timedelta(hours=1)
    stmt = select(Attendance).where(
        and_(
            Attendance.course_id == course_id,
            Attendance.student_id == current_user.id,
            Attendance.create_time > one_hour_ago
        )
    )
    result = await db.execute(stmt)
    if result.scalars().first():
        return {"message": "Already signed in"}
        
    # 创建签到记录
    new_attendance = Attendance(
        course_id=course_id,
        teacher_id=info["teacher_id"],
        student_id=current_user.id,
        status=AttendanceStatus.PRESENT.value,
        sign_time=datetime.now()
    )
    
    db.add(new_attendance)
    await db.commit()
    
    # 实时推送给教师
    # 假设教师在线，可以通过 socket 推送
    # 需要获取教师的 socket_id (这里简化处理，实际应通过 socket_manager)
    # await sio.emit('attendance_update', {...}, to=teacher_sid)
    
    return {"message": "Sign in success"}


@router.get("/list", response_model=List[AttendanceResponse])
async def get_attendance_list(
    course_id: int,
    date: Optional[str] = None, # YYYY-MM-DD
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    查询点名记录
    """
    query = select(Attendance).where(Attendance.course_id == course_id)
    
    if date:
        try:
            target_date = datetime.strptime(date, "%Y-%m-%d")
            next_date = target_date + timedelta(days=1)
            query = query.where(
                and_(
                    Attendance.create_time >= target_date,
                    Attendance.create_time < next_date
                )
            )
        except ValueError:
            pass
            
    query = query.order_by(desc(Attendance.create_time))
    
    result = await db.execute(query)
    records = result.scalars().all()
    
    # 填充学生姓名
    # Data adaptation for Vuetify:
    # Status colors: unSigned->#9E9E9E, signed->#4CAF50, late->#FF9800, leave->#9C27B0
    response_list = []
    for record in records:
        # 获取学生姓名 (假设 User.username 对应 Student.name)
        u_res = await db.execute(select(User.username).where(User.id == record.student_id))
        student_name = u_res.scalar()
        
        resp = AttendanceResponse.model_validate(record)
        resp.student_name = student_name
        response_list.append(resp)
        
    return response_list


@router.put("/update")
async def update_attendance(
    data: AttendanceUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    教师手动修改签到状态
    """
    if current_user.role != "teacher":
        raise HTTPException(status_code=403, detail="Only teachers can update")
        
    stmt = select(Attendance).where(Attendance.id == data.id)
    result = await db.execute(stmt)
    record = result.scalars().first()
    
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
        
    record.status = data.status.value
    if data.remark:
        record.remark = data.remark
        
    await db.commit()
    
    return {"message": "Update success"}
