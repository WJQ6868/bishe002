"""
教师教学管理 - 作业 API
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, desc
from typing import List, Optional
from datetime import datetime

from ..database import get_db
from ..models.teaching import Homework, HomeworkSubmit, HomeworkStatus
from ..models.course import Course
from ..models.user import User
from ..schemas.teaching import HomeworkCreate, HomeworkResponse, HomeworkSubmitCreate, HomeworkSubmitResponse, HomeworkGrade
from ..dependencies.auth import get_current_user

router = APIRouter(prefix="/homework", tags=["作业管理"])


@router.post("/create", response_model=HomeworkResponse)
async def create_homework(
    data: HomeworkCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    布置作业
    """
    if current_user.role != "teacher":
        raise HTTPException(status_code=403, detail="Only teachers can create homework")
        
    new_homework = Homework(
        title=data.title,
        course_id=data.course_id,
        teacher_id=current_user.id,
        content=data.content,
        deadline=data.deadline,
        type=data.type.value,
        score=data.score,
        file_url=data.file_url
    )
    
    db.add(new_homework)
    await db.commit()
    await db.refresh(new_homework)
    
    return HomeworkResponse.model_validate(new_homework)


@router.get("/list", response_model=List[HomeworkResponse])
async def get_homework_list(
    course_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    查询作业列表
    """
    query = select(Homework)
    
    if current_user.role == "teacher":
        query = query.where(Homework.teacher_id == current_user.id)
    elif current_user.role == "student":
        # 学生只能看自己选的课的作业 (简化逻辑：查询所有作业，前端过滤)
        # 实际应关联 CourseSelection
        pass
        
    if course_id:
        query = query.where(Homework.course_id == course_id)
        
    query = query.order_by(desc(Homework.create_time))
    
    result = await db.execute(query)
    homeworks = result.scalars().all()
    
    response_list = []
    for hw in homeworks:
        c_res = await db.execute(select(Course.name).where(Course.id == hw.course_id))
        course_name = c_res.scalar()
        
        resp = HomeworkResponse.model_validate(hw)
        resp.course_name = course_name
        response_list.append(resp)
        
    return response_list


@router.post("/submit", response_model=HomeworkSubmitResponse)
async def submit_homework(
    data: HomeworkSubmitCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    学生提交作业
    """
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="Only students can submit homework")
        
    # 检查是否已提交
    # Data adaptation for Vuetify:
    # Status icons: pending->mdi-clock, corrected->mdi-check, redo->mdi-refresh
    stmt = select(HomeworkSubmit).where(
        and_(
            HomeworkSubmit.homework_id == data.homework_id,
            HomeworkSubmit.student_id == current_user.id
        )
    )
    result = await db.execute(stmt)
    existing = result.scalars().first()
    
    if existing:
        # 更新提交
        existing.content = data.content
        existing.file_url = data.file_url
        existing.status = HomeworkStatus.SUBMITTED.value
        existing.submit_time = datetime.now()
        await db.commit()
        await db.refresh(existing)
        return HomeworkSubmitResponse.model_validate(existing)
    else:
        # 新增提交
        new_submit = HomeworkSubmit(
            homework_id=data.homework_id,
            student_id=current_user.id,
            content=data.content,
            file_url=data.file_url,
            status=HomeworkStatus.SUBMITTED.value
        )
        db.add(new_submit)
        await db.commit()
        await db.refresh(new_submit)
        return HomeworkSubmitResponse.model_validate(new_submit)


@router.post("/grade")
async def grade_homework(
    data: HomeworkGrade,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    教师批改作业
    """
    if current_user.role != "teacher":
        raise HTTPException(status_code=403, detail="Only teachers can grade")
        
    stmt = select(HomeworkSubmit).where(HomeworkSubmit.id == data.submit_id)
    result = await db.execute(stmt)
    submit = result.scalars().first()
    
    if not submit:
        raise HTTPException(status_code=404, detail="Submission not found")
        
    submit.score = data.score
    submit.comment = data.comment
    submit.status = data.status.value
    
    await db.commit()
    
    return {"message": "Grading success"}
