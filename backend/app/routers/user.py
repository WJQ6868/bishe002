from fastapi import APIRouter, Depends, Query, HTTPException, Body, Request
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import List, Optional, Any
from datetime import datetime

from ..database import get_db
from ..models.user import User, UserProfile
from ..models.student import Student
from ..models.academic import AcademicStudent, AcademicClass, AcademicMajor
from ..models.course import Teacher
from ..models.admin import Admin
from ..dependencies.auth import get_current_admin, get_password_hash
from ..schemas.user import UserOut, UserCreate, UserUpdate

router = APIRouter(prefix="/admin/user", tags=["User Management"])

def _optional_str(value: Any) -> Optional[str]:
    if value is None:
        return None
    return str(value)


def _normalized_major(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    value = str(value).strip()
    if not value:
        return None
    if set(value) == {"?"}:
        return None
    return value

@router.get("/list", response_model=List[UserOut])
async def list_users(
    keyword: Optional[str] = Query(None),
    role: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
    request: Request = None,
):
    try:
        if request:
            auth_header = request.headers.get("authorization")
            if not auth_header:
                logger.warning("Access to /admin/user/list without Authorization header")
        stmt = select(User, UserProfile).outerjoin(UserProfile, UserProfile.user_id == User.id)
        if role:
            stmt = stmt.where(User.role == role)
        
        result = await db.execute(stmt)
        rows = result.all()
        
        # Optimize by fetching related data in batches
        student_ids = [u.username for u, p in rows if u.role == 'student']
        teacher_ids = [u.username for u, p in rows if u.role == 'teacher']
        admin_ids = [u.username for u, p in rows if u.role == 'admin']
        
        students = {}
        academic_major_map: dict[str, str] = {}
        if student_ids:
            # Only select fields that actually exist in the Student model
            stmt = select(Student).where(Student.id.in_(student_ids))
            res = await db.execute(stmt)
            students = {s.id: s for s in res.scalars()}

            academic_stmt = (
                select(AcademicStudent.student_code, AcademicMajor.name)
                .join(AcademicClass, AcademicClass.id == AcademicStudent.class_id)
                .join(AcademicMajor, AcademicMajor.id == AcademicClass.major_id)
                .where(AcademicStudent.student_code.in_(student_ids))
            )
            academic_res = await db.execute(academic_stmt)
            academic_major_map = {
                str(code): name for code, name in academic_res if code and name
            }
            
        teachers = {}
        if teacher_ids:
            # Only select fields that actually exist in the Teacher model
            stmt = select(Teacher).where(Teacher.id.in_(teacher_ids))
            res = await db.execute(stmt)
            teachers = {t.id: t for t in res.scalars()}
            
        admins = {}
        if admin_ids:
            # Only select fields that actually exist in the Admin model
            stmt = select(Admin).where(Admin.id.in_(admin_ids))
            res = await db.execute(stmt)
            admins = {a.id: a for a in res.scalars()}
            
        items = []
        normalized_keyword = keyword.strip().lower() if keyword else None

        for user, profile in rows:
            account = user.username
            role_val = user.role
            name = _optional_str(profile.name if profile else None)
            dept = _optional_str(profile.dept if profile else None)
            grade = _optional_str(profile.grade if profile else None)
            entry_time = profile.entry_time.isoformat() if profile and profile.entry_time else None
            
            if role_val == 'student' and account in students:
                s = students[account]
                name = name or _optional_str(s.name)
                dept = _normalized_major(s.major) or academic_major_map.get(account) or dept
                grade = _optional_str(s.grade) or grade
            elif role_val == 'teacher' and account in teachers:
                t = teachers[account]
                name = name or _optional_str(t.name)
            elif role_val == 'admin' and account in admins:
                a = admins[account]
                name = name or _optional_str(a.name)
                dept = _optional_str(a.dept) or dept

            if normalized_keyword:
                search_str = f"{account} {name} {dept} {grade}".lower()
                if normalized_keyword not in search_str:
                    continue
            
            items.append(UserOut(
                id=user.id,
                account=account,
                name=name,
                role=role_val,
                dept=dept,
                grade=grade,
                entryTime=entry_time,
                status=user.is_active,
                createTime=profile.create_time.isoformat() if profile and profile.create_time else None
            ))
        return items
    except Exception as e:
        logger.error(f"Error listing users: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/add", response_model=UserOut)
async def create_user(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    res = await db.execute(select(User).where(User.username == user_data.account))
    if res.scalars().first():
        raise HTTPException(status_code=400, detail="Account already exists")
    
    hashed_pw = get_password_hash(user_data.password)
    new_user = User(
        username=user_data.account,
        password=hashed_pw,
        role=user_data.role,
        is_active=True
    )
    db.add(new_user)
    await db.flush()
    
    profile = UserProfile(
        user_id=new_user.id,
        name=user_data.name,
        dept=user_data.dept,
        grade=user_data.grade,
        entry_time=datetime.fromisoformat(user_data.entry_time) if user_data.entry_time else None,
        create_time=datetime.now()
    )
    db.add(profile)
    
    if user_data.role == 'student':
        db.add(Student(id=user_data.account, name=user_data.name, major=user_data.dept or "Unknown", grade=user_data.grade or "2024"))
    elif user_data.role == 'teacher':
        db.add(Teacher(id=user_data.account, name=user_data.name))
    elif user_data.role == 'admin':
        db.add(Admin(id=user_data.account, name=user_data.name, dept=user_data.dept))
        
    await db.commit()
    await db.refresh(new_user)
    
    return UserOut(
        id=new_user.id,
        account=new_user.username,
        name=user_data.name,
        role=new_user.role,
        dept=user_data.dept,
        grade=user_data.grade,
        entryTime=user_data.entry_time,
        status=True,
        createTime=profile.create_time.isoformat()
    )

@router.put("/edit", response_model=UserOut)
async def update_user(
    user_id: int = Query(...),
    user_data: UserUpdate = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    res = await db.execute(select(User).where(User.id == user_id))
    user = res.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    if user_data.status is not None:
        user.is_active = user_data.status
        
    res = await db.execute(select(UserProfile).where(UserProfile.user_id == user_id))
    profile = res.scalars().first()
    if profile:
        if user_data.name is not None: profile.name = user_data.name
        if user_data.dept is not None: profile.dept = user_data.dept
        if user_data.grade is not None: profile.grade = user_data.grade
        if user_data.entry_time is not None: profile.entry_time = datetime.fromisoformat(user_data.entry_time)
        
    if user.role == 'student':
        res = await db.execute(select(Student).where(Student.id == user.username))
        student = res.scalars().first()
        if student:
            if user_data.name: student.name = user_data.name
            if user_data.dept: student.major = user_data.dept
            if user_data.grade: student.grade = user_data.grade
    elif user.role == 'teacher':
        res = await db.execute(select(Teacher).where(Teacher.id == user.username))
        teacher = res.scalars().first()
        if teacher:
            if user_data.name: teacher.name = user_data.name
    elif user.role == 'admin':
        res = await db.execute(select(Admin).where(Admin.id == user.username))
        admin = res.scalars().first()
        if admin:
            if user_data.name: admin.name = user_data.name
            if user_data.dept: admin.dept = user_data.dept
            
    await db.commit()
    await db.refresh(user)
    
    return UserOut(
        id=user.id,
        account=user.username,
        name=user_data.name or (profile.name if profile else None),
        role=user.role,
        dept=user_data.dept or (profile.dept if profile else None),
        grade=user_data.grade or (profile.grade if profile else None),
        entryTime=user_data.entry_time or (profile.entry_time.isoformat() if profile and profile.entry_time else None),
        status=user.is_active,
        createTime=profile.create_time.isoformat() if profile and profile.create_time else None
    )

@router.put("/status")
async def update_status(
    user_id: int = Body(..., embed=True),
    status: bool = Body(..., embed=True),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    res = await db.execute(select(User).where(User.id == user_id))
    user = res.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = status
    await db.commit()
    return {"message": "Status updated"}

@router.delete("/delete")
async def delete_user(
    user_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    res = await db.execute(select(User).where(User.id == user_id))
    user = res.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    username = user.username
    role = user.role
    
    if role == 'student':
        await db.execute(delete(Student).where(Student.id == username))
    elif role == 'teacher':
        await db.execute(delete(Teacher).where(Teacher.id == username))
    elif role == 'admin':
        await db.execute(delete(Admin).where(Admin.id == username))
        
    await db.execute(delete(UserProfile).where(UserProfile.user_id == user_id))
    await db.execute(delete(User).where(User.id == user_id))
    
    await db.commit()
    return {"message": "Deleted successfully", "user_id": user_id}

@router.post("/reset-password")
async def reset_password(
    user_id: int = Body(..., embed=True),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    res = await db.execute(select(User).where(User.id == user_id))
    user = res.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    hashed_pw = get_password_hash("123456")
    user.password = hashed_pw
    await db.commit()
    return {"message": "Password reset to 123456"}
