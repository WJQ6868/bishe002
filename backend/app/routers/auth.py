from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import timedelta
from loguru import logger

from ..database import get_db
from ..models.user import User, UserProfile
from ..models.student import Student
from ..models.course import Teacher
from ..models.admin import Admin
from ..models.admin_user import StudentUser, TeacherUser
from ..dependencies.auth import (
    verify_password,
    get_password_hash,
    create_access_token,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    get_current_user,
)
from pydantic import BaseModel

router = APIRouter(tags=["Authentication"])


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


class ForgotPasswordRequest(BaseModel):
    username: str
    role: str
    name: str
    new_password: str

@router.post("/token")
async def login_for_access_token(request: Request, db: AsyncSession = Depends(get_db)):
    username = None
    password = None
    selected_role = None  # 前端选择的角色
    ct = request.headers.get("content-type", "")
    if ct.startswith("application/json"):
        data = await request.json()
        username = data.get("username")
        password = data.get("password")
        selected_role = data.get("role")  # 获取前端选择的角色
    else:
        try:
            form = await request.form()
            username = form.get("username")
            password = form.get("password")
            selected_role = form.get("role")
        except Exception:
            body = (await request.body()).decode()
            from urllib.parse import parse_qs
            params = parse_qs(body)
            username = (params.get("username") or [None])[0]
            password = (params.get("password") or [None])[0]
            selected_role = (params.get("role") or [None])[0]

    if not username or not password:
        logger.warning(f"Login failed: Missing username or password")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="username/password required")

    # 验证账号格式和角色匹配
    if selected_role:
        # 8开头的6位数只能是管理员
        if username.startswith('8') and len(username) == 6:
            if selected_role != 'admin':
                logger.warning(f"Login failed: Admin account {username} trying to login as {selected_role}")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="该账号只能以管理员身份登录"
                )
        # 1开头的6位数只能是教师
        elif username.startswith('1') and len(username) == 6:
            if selected_role != 'teacher':
                logger.warning(f"Login failed: Teacher account {username} trying to login as {selected_role}")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="该账号只能以教师身份登录"
                )
        # 2开头的8位数只能是学生
        elif username.startswith('2') and len(username) == 8:
            if selected_role != 'student':
                logger.warning(f"Login failed: Student account {username} trying to login as {selected_role}")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="该账号只能以学生身份登录"
                )

    logger.info(f"Login attempt for user: {username}")
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalars().first()

    if not user:
        logger.warning(f"Login failed: User {username} not found")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 验证密码
    if not verify_password(password, user.password):
        logger.warning(f"Login failed: Incorrect password for user {username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 验证选择的角色与数据库中的角色一致
    if selected_role and selected_role != user.role:
        logger.warning(f"Login failed: Role mismatch for user {username}. Selected: {selected_role}, Actual: {user.role}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"角色不匹配，该账号是{get_role_name(user.role)}账号，请切换到正确的角色登录",
        )
    
    # Create token
    logger.info(f"Login successful for user: {username}")
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role},
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


def get_role_name(role: str) -> str:
    """获取角色中文名称"""
    role_names = {
        "student": "学生",
        "teacher": "教师",
        "admin": "管理员"
    }
    return role_names.get(role, role)


@router.post("/auth/forgot-password")
async def forgot_password(
    payload: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    username = payload.username.strip()
    role = payload.role.strip()
    name = payload.name.strip()
    new_password = payload.new_password.strip()

    if not username or not role or not name or not new_password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请完整填写账号、角色、姓名和新密码")
    if len(new_password) < 6:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="新密码长度不能少于6位")

    res = await db.execute(select(User).where(User.username == username))
    user = res.scalars().first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="账号不存在")
    if user.role != role:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="角色与账号不匹配")

    matched = False
    profile_res = await db.execute(select(UserProfile).where(UserProfile.user_id == user.id))
    profile = profile_res.scalars().first()
    if profile and profile.name and profile.name.strip() == name:
        matched = True

    if not matched:
        if role == "student":
            student_res = await db.execute(select(Student).where(Student.id == username))
            student = student_res.scalars().first()
            if student and student.name == name:
                matched = True
            if not matched:
                student_user_res = await db.execute(select(StudentUser).where(StudentUser.student_no == username))
                student_user = student_user_res.scalars().first()
                if student_user and student_user.name == name:
                    matched = True
        elif role == "teacher":
            teacher_res = await db.execute(select(Teacher).where(Teacher.id == username))
            teacher = teacher_res.scalars().first()
            if teacher and teacher.name == name:
                matched = True
            if not matched:
                teacher_user_res = await db.execute(select(TeacherUser).where(TeacherUser.teacher_no == username))
                teacher_user = teacher_user_res.scalars().first()
                if teacher_user and teacher_user.name == name:
                    matched = True
        elif role == "admin":
            admin_res = await db.execute(select(Admin).where(Admin.id == username))
            admin = admin_res.scalars().first()
            if admin and admin.name == name:
                matched = True

    if not matched:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="姓名与账号不匹配，请联系管理员")

    user.password = get_password_hash(new_password)
    await db.commit()
    return {"message": "Password reset successful"}


@router.post("/auth/change-password")
async def change_password(
    payload: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Self-service password change for any logged-in user (students included)
    # Accept legacy plain-text passwords to allow upgrade on first change
    if not verify_password(payload.old_password, current_user.password) and payload.old_password != current_user.password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="原密码错误")
    current_user.password = get_password_hash(payload.new_password)
    await db.commit()
    return {"message": "Password updated"}


@router.get("/auth/me")
async def read_current_user(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    profile_stmt = select(UserProfile).where(UserProfile.user_id == current_user.id)
    result = await db.execute(profile_stmt)
    profile = result.scalars().first()

    return {
        "id": current_user.id,
        "username": current_user.username,
        "role": current_user.role,
        "name": profile.name if profile and profile.name else current_user.username,
        "dept": profile.dept if profile else None,
        "grade": profile.grade if profile else None,
        "entry_time": profile.entry_time.isoformat() if profile and profile.entry_time else None,
    }
