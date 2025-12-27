from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from datetime import datetime
import json

from ..database import get_db
from ..models.user import User, UserProfile
from ..models.admin_user import TeacherUser
from ..models.course import Teacher
from ..dependencies.auth import get_current_user, get_password_hash
from pydantic import BaseModel, Field

router = APIRouter(prefix="/admin/teacher", tags=["admin-teacher"])


class TeacherCreate(BaseModel):
    teacher_no: Optional[str] = None
    name: str
    gender: int
    age: Optional[int] = None
    mobile: Optional[str] = None
    email: Optional[str] = None
    dept_id: int
    post_type: int
    subject: Optional[str] = None
    title: Optional[int] = None
    entry_time: Optional[datetime] = None
    leave_status: int = 1
    teach_years: Optional[int] = None
    role: Optional[str] = None
    permissions: dict = Field(default_factory=dict)
    status: int = 1


class TeacherUpdate(BaseModel):
    name: Optional[str] = None
    gender: Optional[int] = None
    age: Optional[int] = None
    mobile: Optional[str] = None
    email: Optional[str] = None
    dept_id: Optional[int] = None
    post_type: Optional[int] = None
    subject: Optional[str] = None
    title: Optional[int] = None
    entry_time: Optional[datetime] = None
    leave_status: Optional[int] = None
    teach_years: Optional[int] = None
    role: Optional[str] = None
    permissions: Optional[dict] = None
    status: Optional[int] = None


class TeacherOut(BaseModel):
    id: int
    teacher_no: str
    name: str
    gender: int
    age: Optional[int]
    mobile: Optional[str]
    email: Optional[str]
    dept_id: int
    post_type: int
    subject: Optional[str]
    title: Optional[int]
    entry_time: Optional[datetime]
    leave_status: int
    teach_years: Optional[int]
    role: Optional[str]
    permissions: Optional[dict]
    status: int
    last_login_time: Optional[datetime]
    last_login_ip: Optional[str]
    create_time: datetime
    update_time: datetime

    class Config:
        orm_mode = True


class TeacherPasswordUpdate(BaseModel):
    password: str


def _ensure_admin(current_user: User):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admin can access")


def _dict_permissions(value: Optional[dict]) -> str:
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=False)


def _normalize_optional_str(value: Optional[str]) -> Optional[str]:
    """Return None for empty/whitespace strings so unique constraints don't clash on ''."""
    if value is None:
        return None
    trimmed = value.strip()
    return trimmed or None


async def _get_user_by_username(db: AsyncSession, username: str) -> Optional[User]:
    res = await db.execute(select(User).where(User.username == username))
    return res.scalars().first()


async def _next_teacher_no(db: AsyncSession) -> str:
    res = await db.execute(select(TeacherUser.teacher_no))
    nos = [int(x) for x in res.scalars().all() if str(x).isdigit()]
    base = 100001
    if not nos:
        return str(base)
    return str(max(nos) + 1)


@router.get("/list", response_model=List[TeacherOut])
async def list_teachers(
    dept_id: Optional[int] = None,
    post_type: Optional[int] = None,
    title: Optional[int] = None,
    status: Optional[int] = None,
    keyword: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    _ensure_admin(current_user)
    query = select(TeacherUser)
    if dept_id:
        query = query.where(TeacherUser.dept_id == dept_id)
    if post_type:
        query = query.where(TeacherUser.post_type == post_type)
    if title:
        query = query.where(TeacherUser.title == title)
    if status:
        query = query.where(TeacherUser.status == status)
    if keyword:
        like = f"%{keyword}%"
        query = query.where(TeacherUser.name.ilike(like) | TeacherUser.teacher_no.ilike(like))
    res = await db.execute(query)
    rows = res.scalars().all()
    for r in rows:
        if r.permissions and isinstance(r.permissions, str):
            try:
                r.permissions = json.loads(r.permissions)
            except Exception:
                pass
    return rows


@router.post("/add", response_model=TeacherOut)
async def add_teacher(payload: TeacherCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    _ensure_admin(current_user)
    teacher_no = payload.teacher_no or await _next_teacher_no(db)
    mobile = _normalize_optional_str(payload.mobile)
    email = _normalize_optional_str(payload.email)
    # uniqueness
    dup = await db.execute(select(TeacherUser).where(TeacherUser.teacher_no == teacher_no))
    if dup.scalars().first():
        raise HTTPException(status_code=400, detail="teacher_no already exists")
    if mobile:
        dup = await db.execute(select(TeacherUser).where(TeacherUser.mobile == mobile))
        if dup.scalars().first():
            raise HTTPException(status_code=400, detail="mobile already exists")
    if email:
        dup = await db.execute(select(TeacherUser).where(TeacherUser.email == email))
        if dup.scalars().first():
            raise HTTPException(status_code=400, detail="email already exists")

    db_obj = TeacherUser(
        teacher_no=teacher_no,
        name=payload.name,
        gender=payload.gender,
        age=payload.age,
        mobile=mobile,
        email=email,
        dept_id=payload.dept_id,
        post_type=payload.post_type,
        subject=payload.subject,
        title=payload.title,
        entry_time=payload.entry_time,
        leave_status=payload.leave_status,
        teach_years=payload.teach_years,
        role=payload.role,
        permissions=_dict_permissions(payload.permissions),
        status=payload.status,
    )
    db.add(db_obj)

    # sync sys_users
    existing_sys = await _get_user_by_username(db, teacher_no)
    if not existing_sys:
        sys_user = User(
            username=teacher_no,
            password=get_password_hash("123456"),
            role="teacher",
            is_active=payload.status == 1,
        )
        db.add(sys_user)
        await db.flush()
        profile = UserProfile(user_id=sys_user.id, name=payload.name, dept=str(payload.dept_id))
        db.add(profile)

    # sync legacy teachers table for course selection
    legacy_teacher = await db.execute(select(Teacher).where(Teacher.id == teacher_no))
    if not legacy_teacher.scalars().first():
        db.add(Teacher(id=teacher_no, name=payload.name))

    await db.commit()
    await db.refresh(db_obj)
    if db_obj.permissions and isinstance(db_obj.permissions, str):
        try:
            db_obj.permissions = json.loads(db_obj.permissions)
        except Exception:
            pass
    return db_obj


@router.put("/{teacher_id}", response_model=TeacherOut)
async def update_teacher(teacher_id: int, payload: TeacherUpdate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    _ensure_admin(current_user)
    res = await db.execute(select(TeacherUser).where(TeacherUser.id == teacher_id))
    obj = res.scalars().first()
    if not obj:
        raise HTTPException(status_code=404, detail="Teacher not found")

    mobile = _normalize_optional_str(payload.mobile) if payload.mobile is not None else None
    email = _normalize_optional_str(payload.email) if payload.email is not None else None

    # unique checks
    if mobile:
        dup = await db.execute(select(TeacherUser).where(TeacherUser.mobile == mobile, TeacherUser.id != teacher_id))
        if dup.scalars().first():
            raise HTTPException(status_code=400, detail="mobile already exists")
    if email:
        dup = await db.execute(select(TeacherUser).where(TeacherUser.email == email, TeacherUser.id != teacher_id))
        if dup.scalars().first():
            raise HTTPException(status_code=400, detail="email already exists")

    update_data = payload.dict(exclude_unset=True)
    if "mobile" in update_data:
        update_data["mobile"] = mobile
    if "email" in update_data:
        update_data["email"] = email

    for field, value in update_data.items():
        if field == "permissions" and value is not None:
            setattr(obj, field, _dict_permissions(value))
        else:
            setattr(obj, field, value)
    obj.update_time = datetime.now()

    # sync sys_users active
    if payload.status == 2 or payload.leave_status == 2:
        sys = await _get_user_by_username(db, obj.teacher_no)
        if sys:
            sys.is_active = False
    await db.commit()
    await db.refresh(obj)

    # keep legacy teachers table name in sync
    legacy_teacher = await db.execute(select(Teacher).where(Teacher.id == obj.teacher_no))
    t = legacy_teacher.scalars().first()
    if t:
        if payload.name:
            t.name = payload.name
        await db.commit()
    if obj.permissions and isinstance(obj.permissions, str):
        try:
            obj.permissions = json.loads(obj.permissions)
        except Exception:
            pass
    return obj


@router.put("/{teacher_id}/password")
async def update_teacher_password(
    teacher_id: int,
    payload: TeacherPasswordUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_admin(current_user)
    res = await db.execute(select(TeacherUser).where(TeacherUser.id == teacher_id))
    obj = res.scalars().first()
    if not obj:
        raise HTTPException(status_code=404, detail="Teacher not found")
    sys_user = await _get_user_by_username(db, obj.teacher_no)
    if not sys_user:
        raise HTTPException(status_code=404, detail="Related account not found")
    sys_user.password = get_password_hash(payload.password)
    await db.commit()
    return {"message": "Password updated"}


@router.delete("/{teacher_id}")
async def delete_teacher(teacher_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    _ensure_admin(current_user)
    res = await db.execute(select(TeacherUser).where(TeacherUser.id == teacher_id))
    obj = res.scalars().first()
    if not obj:
        raise HTTPException(status_code=404, detail="Teacher not found")
    await db.delete(obj)
    sys = await _get_user_by_username(db, obj.teacher_no)
    if sys:
        sys.is_active = False
    await db.commit()
    return {"message": "deleted"}
