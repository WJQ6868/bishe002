from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import timedelta
from loguru import logger

from ..database import get_db
from ..models.user import User, UserProfile
from ..dependencies.auth import (
    verify_password,
    create_access_token,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    get_current_user,
)

router = APIRouter(tags=["Authentication"])

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
