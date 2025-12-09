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
    ct = request.headers.get("content-type", "")
    if ct.startswith("application/json"):
        data = await request.json()
        username = data.get("username")
        password = data.get("password")
    else:
        try:
            form = await request.form()
            username = form.get("username")
            password = form.get("password")
        except Exception:
            body = (await request.body()).decode()
            from urllib.parse import parse_qs
            params = parse_qs(body)
            username = (params.get("username") or [None])[0]
            password = (params.get("password") or [None])[0]

    if not username or not password:
        logger.warning(f"Login failed: Missing username or password")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="username/password required")

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

    if not verify_password(password, user.password):
        logger.warning(f"Login failed: Incorrect password for user {username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create token
    logger.info(f"Login successful for user: {username}")
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role},
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


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
