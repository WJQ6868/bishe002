from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Optional

from ..database import get_db
from ..models.course import Course, Teacher
from ..models.student import CourseSelection
from ..schemas.course import (
    CourseCreate,
    CourseUpdate,
    CourseResponse,
    TeacherOptionOut,
)
from ..dependencies.auth import get_current_admin, get_current_user

router = APIRouter(
    prefix="/course",
    tags=["Course Management"]
)

@router.get("/student/list", response_model=List[CourseResponse])
async def list_student_courses(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get courses selected by the current student
    """
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="Only students can access this")

    # 兼容历史数据：course_selections.student_id 可能存学号(username) 或 sys_users.id
    student_keys = [str(current_user.username), str(current_user.id)]
    stmt = (
        select(Course)
        .join(CourseSelection, Course.id == CourseSelection.course_id)
        .where(CourseSelection.student_id.in_(student_keys))
    )
    
    result = await db.execute(stmt)
    courses = result.scalars().all()
    return courses

@router.get("/{course_id}/teacher", response_model=dict)
async def get_course_teacher(
    course_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get teacher info for a course
    """
    stmt = select(Course).where(Course.id == course_id)
    result = await db.execute(stmt)
    course = result.scalars().first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
        
    stmt = select(Teacher).where(Teacher.id == course.teacher_id)
    result = await db.execute(stmt)
    teacher = result.scalars().first()
    
    if not teacher:
         raise HTTPException(status_code=404, detail="Teacher not found")
         
    return {"id": teacher.id, "name": teacher.name}

@router.post("/add", response_model=CourseResponse, status_code=status.HTTP_201_CREATED)
async def create_course(
    course: CourseCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_admin)
):
    # Check if teacher exists
    result = await db.execute(select(Teacher).filter(Teacher.id == course.teacher_id))
    teacher = result.scalars().first()
    if not teacher:
        raise HTTPException(status_code=400, detail="Teacher ID does not exist")

    new_course = Course(**course.dict())
    db.add(new_course)
    await db.commit()
    await db.refresh(new_course)
    return new_course

@router.get("/list", response_model=List[CourseResponse])
async def list_courses(
    course_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user) # All roles can access
):
    query = select(Course)
    if course_type:
        query = query.filter(Course.course_type == course_type)
    
    result = await db.execute(query)
    courses = result.scalars().all()
    return courses

@router.put("/{course_id}", response_model=CourseResponse)
async def update_course(
    course_id: int,
    course_update: CourseUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_admin)
):
    result = await db.execute(select(Course).filter(Course.id == course_id))
    db_course = result.scalars().first()
    
    if not db_course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    incoming_teacher_id = None
    if course_update.teacher_id is not None:
        incoming_teacher_id = str(course_update.teacher_id)
        current_teacher_id = str(db_course.teacher_id) if db_course.teacher_id is not None else None
        if incoming_teacher_id != current_teacher_id:
            t_result = await db.execute(select(Teacher).filter(Teacher.id == incoming_teacher_id))
            teacher = t_result.scalars().first()
            if not teacher:
                raise HTTPException(status_code=400, detail="Teacher ID does not exist")

    update_data = course_update.dict(exclude_unset=True)
    if incoming_teacher_id is not None:
        update_data["teacher_id"] = incoming_teacher_id
    for key, value in update_data.items():
        setattr(db_course, key, value)
    
    await db.commit()
    await db.refresh(db_course)
    return db_course

@router.delete("/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_course(
    course_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_admin)
):
    result = await db.execute(select(Course).filter(Course.id == course_id))
    db_course = result.scalars().first()
    
    if not db_course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    # Check if course is enrolled (TODO: Check Enrollment table)
    # For now, assuming "unselected course" check is manual or no enrollments yet
    
    await db.delete(db_course)
    await db.commit()
    return None


@router.get("/teachers", response_model=list[TeacherOptionOut])
async def list_teachers(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_admin),
):
    result = await db.execute(select(Teacher).order_by(Teacher.id))
    teachers = result.scalars().all()
    return [TeacherOptionOut(id=str(t.id), name=t.name or str(t.id)) for t in teachers]
