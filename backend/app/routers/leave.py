"""
请假管理 - API 路由
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, desc
from typing import List, Optional
from datetime import datetime, timedelta
import shutil
import os

from ..database import get_db
from ..models.leave import LeaveApply, LeaveStatus
from ..models.course import Course, Teacher
from ..models.student import Student, CourseSelection
from ..models.user import User
from ..schemas.leave import LeaveCreate, LeaveResponse, LeaveApprove, LeaveRecall
from ..dependencies.auth import get_current_user
from ..services.socket_manager import sio, online_users

router = APIRouter(prefix="/leave", tags=["请假管理"])

# 文件上传目录
UPLOAD_DIR = "static/uploads/leave"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/apply", response_model=LeaveResponse)
async def apply_leave(
    leave: LeaveCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    提交请假申请
    """
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="Only students can apply for leave")
    
    # 1. 校验课程和任课教师
    stmt = select(Course).where(Course.id == leave.course_id)
    result = await db.execute(stmt)
    course = result.scalars().first()
    
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
        
    # Verify teacher exists in Teacher table
    stmt = select(Teacher).where(Teacher.id == course.teacher_id)
    result = await db.execute(stmt)
    teacher = result.scalars().first()
    
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")
        
    # Find Teacher User account (User.username == Teacher.id)
    stmt = select(User).where(and_(User.username == course.teacher_id, User.role == 'teacher'))
    result = await db.execute(stmt)
    teacher_user = result.scalars().first()
    
    if not teacher_user:
        # Fallback: Try finding by name if username lookup fails (legacy support)
        stmt = select(User).where(and_(User.username == teacher.name, User.role == 'teacher'))
        result = await db.execute(stmt)
        teacher_user = result.scalars().first()
        
        if not teacher_user:
             raise HTTPException(status_code=404, detail="Teacher user account not found")
    
    # 2. 校验时长 (单次 <= 7天)
    duration = leave.end_time - leave.start_time
    if duration.days > 7:
        raise HTTPException(status_code=400, detail="Leave duration cannot exceed 7 days")
        
    # 3. 校验本月累计时长 (<= 14天)
    # 获取本月第一天
    today = datetime.now()
    first_day = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    stmt = select(LeaveApply).where(
        and_(
            LeaveApply.student_id == current_user.id,
            LeaveApply.start_time >= first_day,
            LeaveApply.status == LeaveStatus.APPROVED
        )
    )
    result = await db.execute(stmt)
    history_leaves = result.scalars().all()
    
    total_days = 0
    for l in history_leaves:
        total_days += (l.end_time - l.start_time).days
        
    if total_days + duration.days > 14:
        raise HTTPException(status_code=400, detail="Monthly leave duration cannot exceed 14 days")
        
    # 4. 校验重复申请
    stmt = select(LeaveApply).where(
        and_(
            LeaveApply.student_id == current_user.id,
            LeaveApply.course_id == leave.course_id,
            LeaveApply.status.in_([LeaveStatus.PENDING, LeaveStatus.APPROVED]),
            # 时间重叠校验
            LeaveApply.start_time < leave.end_time,
            LeaveApply.end_time > leave.start_time
        )
    )
    result = await db.execute(stmt)
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="Duplicate leave application for this time slot")

    # 创建申请
    new_leave = LeaveApply(
        student_id=current_user.id,
        course_id=leave.course_id,
        teacher_id=teacher_user.id, # 使用 User ID
        type=leave.type.value,
        start_time=leave.start_time,
        end_time=leave.end_time,
        reason=leave.reason,
        file_url=leave.file_url,
        status=LeaveStatus.PENDING.value
    )
    
    db.add(new_leave)
    await db.commit()
    await db.refresh(new_leave)
    
    # 补充响应信息
    response = LeaveResponse.model_validate(new_leave)
    response.course_name = course.name
    response.teacher_name = teacher.name
    response.student_name = current_user.username # 简单使用 username
    
    # 推送通知给教师
    if teacher_user.id in online_users:
        await sio.emit('new_leave_apply', response.dict(), to=online_users[teacher_user.id])
        
    return response


@router.post("/upload")
async def upload_proof(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """
    上传证明材料
    """
    if not file.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.pdf')):
        raise HTTPException(status_code=400, detail="Only images and PDF are allowed")
        
    # 生成文件名
    timestamp = int(datetime.now().timestamp())
    filename = f"{current_user.id}_{timestamp}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    # 返回相对路径
    return {"url": f"/static/uploads/leave/{filename}"}


@router.get("/student/list", response_model=dict)
async def get_student_leaves(
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    学生查询请假记录 (分页适配 Vuetify)
    """
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="Only students can access")
        
    query = select(LeaveApply).where(LeaveApply.student_id == current_user.id)
    
    if status:
        query = query.where(LeaveApply.status == status)
        
    # Count total
    count_stmt = select(func.count()).select_from(query.subquery())
    total_res = await db.execute(count_stmt)
    total = total_res.scalar()
    
    # Pagination
    query = query.order_by(desc(LeaveApply.create_time)).offset((page - 1) * limit).limit(limit)
    
    result = await db.execute(query)
    leaves = result.scalars().all()
    
    # 填充额外信息 (Course Name, Teacher Name)
    response_list = []
    for leave in leaves:
        # 获取课程名
        c_res = await db.execute(select(Course.name).where(Course.id == leave.course_id))
        course_name = c_res.scalar()
        
        # 获取教师名
        u_res = await db.execute(select(User.username).where(User.id == leave.teacher_id))
        teacher_username = u_res.scalar()
        
        teacher_name = teacher_username
        if teacher_username:
            t_res = await db.execute(select(Teacher.name).where(Teacher.id == teacher_username))
            real_name = t_res.scalar()
            if real_name:
                teacher_name = real_name
        
        resp = LeaveResponse.model_validate(leave)
        resp.course_name = course_name
        resp.teacher_name = teacher_name
        response_list.append(resp)
        
    return {
        "items": response_list,
        "total": total,
        "page": page,
        "limit": limit
    }


@router.get("/teacher/list", response_model=List[LeaveResponse])
async def get_teacher_leaves(
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    教师查询待审批申请
    """
    if current_user.role != "teacher":
        raise HTTPException(status_code=403, detail="Only teachers can access")
        
    query = select(LeaveApply).where(LeaveApply.teacher_id == current_user.id)
    
    if status:
        query = query.where(LeaveApply.status == status)
        
    query = query.order_by(desc(LeaveApply.create_time))
    
    result = await db.execute(query)
    leaves = result.scalars().all()
    
    # 填充额外信息
    response_list = []
    for leave in leaves:
        c_res = await db.execute(select(Course.name).where(Course.id == leave.course_id))
        course_name = c_res.scalar()
        
        # 获取学生名
        u_res = await db.execute(select(User.username).where(User.id == leave.student_id))
        student_username = u_res.scalar()
        
        student_name = student_username
        if student_username:
            s_res = await db.execute(select(Student.name).where(Student.id == student_username))
            real_name = s_res.scalar()
            if real_name:
                student_name = real_name
        
        resp = LeaveResponse.model_validate(leave)
        resp.course_name = course_name
        resp.student_name = student_name
        response_list.append(resp)
        
    return response_list


@router.post("/approve")
async def approve_leave(
    approve: LeaveApprove,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    教师审批申请
    """
    if current_user.role != "teacher":
        raise HTTPException(status_code=403, detail="Only teachers can approve")
        
    stmt = select(LeaveApply).where(LeaveApply.id == approve.leave_id)
    result = await db.execute(stmt)
    leave = result.scalars().first()
    
    if not leave:
        raise HTTPException(status_code=404, detail="Leave application not found")
        
    if leave.teacher_id != current_user.id:
        raise HTTPException(status_code=403, detail="You are not the approver for this application")
        
    if leave.status != LeaveStatus.PENDING.value:
        raise HTTPException(status_code=400, detail="Application is not pending")
        
    if approve.result == "rejected" and not approve.opinion:
        raise HTTPException(status_code=400, detail="Opinion is required for rejection")
        
    leave.status = approve.result
    leave.opinion = approve.opinion
    leave.approve_time = datetime.now()
    
    await db.commit()
    
    # 推送通知给学生
    if leave.student_id in online_users:
        await sio.emit('leave_status_change', {
            'leave_id': leave.id,
            'status': leave.status,
            'opinion': leave.opinion
        }, to=online_users[leave.student_id])
        
    return {"code": 0, "message": "success"}


@router.post("/recall")
async def recall_leave(
    recall: LeaveRecall,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    学生撤回申请
    """
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="Only students can recall")
        
    stmt = select(LeaveApply).where(LeaveApply.id == recall.leave_id)
    result = await db.execute(stmt)
    leave = result.scalars().first()
    
    if not leave:
        raise HTTPException(status_code=404, detail="Leave application not found")
        
    if leave.student_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only recall your own application")
        
    if leave.status != LeaveStatus.PENDING.value:
        raise HTTPException(status_code=400, detail="Only pending applications can be recalled")
        
    leave.status = LeaveStatus.RECALLED.value
    await db.commit()
    
    return {"code": 0, "message": "success"}
