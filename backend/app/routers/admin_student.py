from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from datetime import datetime
import json

from ..database import get_db
from ..models.user import User, UserProfile
from ..models.admin_user import StudentUser
from ..models.student import Student
from ..dependencies.auth import get_current_user, get_password_hash
from pydantic import BaseModel, Field

router = APIRouter(prefix="/admin/student", tags=["admin-student"])


class StudentCreate(BaseModel):
    student_no: Optional[str] = None
    name: str
    gender: int
    age: Optional[int] = None
    mobile: Optional[str] = None
    parent_mobile: str
    grade_id: int
    class_id: int
    major: Optional[str] = None
    enrollment_time: Optional[datetime] = None
    student_status: int = 1
    role: Optional[str] = None
    permissions: dict = Field(default_factory=dict)
    status: int = 1


class StudentUpdate(BaseModel):
    name: Optional[str] = None
    gender: Optional[int] = None
    age: Optional[int] = None
    mobile: Optional[str] = None
    parent_mobile: Optional[str] = None
    grade_id: Optional[int] = None
    class_id: Optional[int] = None
    major: Optional[str] = None
    enrollment_time: Optional[datetime] = None
    student_status: Optional[int] = None
    role: Optional[str] = None
    permissions: Optional[dict] = None
    status: Optional[int] = None


class StudentOut(BaseModel):
    id: int
    student_no: str
    name: str
    gender: int
    age: Optional[int]
    mobile: Optional[str]
    parent_mobile: str
    grade_id: int
    class_id: int
    major: Optional[str]
    enrollment_time: Optional[datetime]
    student_status: int
    role: Optional[str]
    permissions: Optional[dict]
    status: int
    last_login_time: Optional[datetime]
    last_login_ip: Optional[str]
    create_time: datetime
    update_time: datetime

    class Config:
        orm_mode = True


class StudentPasswordUpdate(BaseModel):
    password: str


def _ensure_admin(current_user: User):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admin can access")


def _dict_permissions(value: Optional[dict]) -> str:
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=False)


async def _get_user_by_username(db: AsyncSession, username: str) -> Optional[User]:
    res = await db.execute(select(User).where(User.username == username))
    return res.scalars().first()


async def _next_student_no(db: AsyncSession) -> str:
    res = await db.execute(select(StudentUser.student_no))
    nos = [int(x) for x in res.scalars().all() if str(x).isdigit()]
    base = 20230001
    if not nos:
        return str(base)
    return str(max(nos) + 1)


@router.get("/list", response_model=List[StudentOut])
async def list_students(
    grade_id: Optional[int] = None,
    class_id: Optional[int] = None,
    student_status: Optional[int] = None,
    status: Optional[int] = None,
    keyword: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    _ensure_admin(current_user)
    query = select(StudentUser)
    if grade_id is not None:
        query = query.where(StudentUser.grade_id == grade_id)
    if class_id is not None:
        query = query.where(StudentUser.class_id == class_id)
    if student_status is not None:
        query = query.where(StudentUser.student_status == student_status)
    if status is not None:
        query = query.where(StudentUser.status == status)
    if keyword:
        like = f"%{keyword}%"
        query = query.where(StudentUser.name.ilike(like) | StudentUser.student_no.ilike(like))
    res = await db.execute(query)
    rows = res.scalars().all()
    for r in rows:
        if r.permissions and isinstance(r.permissions, str):
            try:
                r.permissions = json.loads(r.permissions)
            except Exception:
                pass
    return rows


@router.post("/add", response_model=StudentOut)
async def add_student(payload: StudentCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    _ensure_admin(current_user)
    student_no = payload.student_no or await _next_student_no(db)
    dup = await db.execute(select(StudentUser).where(StudentUser.student_no == student_no))
    if dup.scalars().first():
        raise HTTPException(status_code=400, detail="student_no already exists")

    db_obj = StudentUser(
        student_no=student_no,
        name=payload.name,
        gender=payload.gender,
        age=payload.age,
        mobile=payload.mobile,
        parent_mobile=payload.parent_mobile,
        grade_id=payload.grade_id,
        class_id=payload.class_id,
        major=payload.major,
        enrollment_time=payload.enrollment_time,
        student_status=payload.student_status,
        role=payload.role,
        permissions=_dict_permissions(payload.permissions),
        status=payload.status,
    )
    db.add(db_obj)

    existing_sys = await _get_user_by_username(db, student_no)
    if not existing_sys:
        sys_user = User(
            username=student_no,
            password=get_password_hash("123456"),
            role="student",
            is_active=payload.status == 1,
        )
        db.add(sys_user)
        await db.flush()
        profile = UserProfile(user_id=sys_user.id, name=payload.name, grade=str(payload.grade_id))
        db.add(profile)

    # sync legacy students table for downstream usage
    legacy_student = await db.execute(select(Student).where(Student.id == student_no))
    if not legacy_student.scalars().first():
        db.add(Student(id=student_no, name=payload.name, major=payload.major or None, grade=str(payload.grade_id) if payload.grade_id else None))

    await db.commit()
    await db.refresh(db_obj)
    if db_obj.permissions and isinstance(db_obj.permissions, str):
        try:
            db_obj.permissions = json.loads(db_obj.permissions)
        except Exception:
            pass
    return db_obj


@router.put("/{student_id}", response_model=StudentOut)
async def update_student(student_id: int, payload: StudentUpdate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    _ensure_admin(current_user)
    res = await db.execute(select(StudentUser).where(StudentUser.id == student_id))
    obj = res.scalars().first()
    if not obj:
        raise HTTPException(status_code=404, detail="Student not found")

    for field, value in payload.dict(exclude_unset=True).items():
        if field == "permissions" and value is not None:
            setattr(obj, field, _dict_permissions(value))
        else:
            setattr(obj, field, value)
    obj.update_time = datetime.now()

    if payload.status == 2 or (payload.student_status and payload.student_status in (4, 5)):
        sys = await _get_user_by_username(db, obj.student_no)
        if sys:
            sys.is_active = False

    await db.commit()
    await db.refresh(obj)

    # keep legacy students table name/grade/major in sync
    legacy_student = await db.execute(select(Student).where(Student.id == obj.student_no))
    s = legacy_student.scalars().first()
    if s:
        if payload.name:
            s.name = payload.name
        if payload.major is not None:
            s.major = payload.major
        if payload.grade_id is not None:
            s.grade = str(payload.grade_id)
        await db.commit()
    if obj.permissions and isinstance(obj.permissions, str):
        try:
            obj.permissions = json.loads(obj.permissions)
        except Exception:
            pass
    return obj


@router.put("/{student_id}/password")
async def update_student_password(
    student_id: int,
    payload: StudentPasswordUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_admin(current_user)
    res = await db.execute(select(StudentUser).where(StudentUser.id == student_id))
    obj = res.scalars().first()
    if not obj:
        raise HTTPException(status_code=404, detail="Student not found")
    sys_user = await _get_user_by_username(db, obj.student_no)
    if not sys_user:
        raise HTTPException(status_code=404, detail="Related account not found")
    sys_user.password = get_password_hash(payload.password)
    await db.commit()
    return {"message": "Password updated"}


@router.delete("/{student_id}")
async def delete_student(student_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    _ensure_admin(current_user)
    res = await db.execute(select(StudentUser).where(StudentUser.id == student_id))
    obj = res.scalars().first()
    if not obj:
        raise HTTPException(status_code=404, detail="Student not found")
    await db.delete(obj)
    sys = await _get_user_by_username(db, obj.student_no)
    if sys:
        sys.is_active = False
    await db.commit()
    return {"message": "deleted"}
