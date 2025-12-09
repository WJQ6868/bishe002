from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
from pydantic import BaseModel

from ..database import get_db
from ..models.quick_link import QuickLink
from ..models.user import User
from ..dependencies.auth import get_current_user

router = APIRouter(prefix="/quick_link", tags=["Quick Links"])
router_hyphen = APIRouter(prefix="/quick-link", tags=["Quick Links"])

class QuickLinkOut(BaseModel):
    id: int
    name: str
    description: str | None
    icon: str | None
    icon_bg: str
    icon_color: str
    route: str

    class Config:
        from_attributes = True

async def _get_links(
    current_user: User,
    db: AsyncSession
):
    query = select(QuickLink).where(QuickLink.is_active == True).order_by(QuickLink.sort_order)
    result = await db.execute(query)
    links = result.scalars().all()
    
    # Filter by role
    user_role = current_user.role
    filtered_links = []
    for link in links:
        if link.roles == "all" or user_role in link.roles.split(","):
            filtered_links.append(link)
    
    return filtered_links

@router.get("/list", response_model=List[QuickLinkOut])
async def get_quick_links(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return await _get_links(current_user, db)

@router_hyphen.get("/list", response_model=List[QuickLinkOut])
async def get_quick_links_hyphen(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return await _get_links(current_user, db)
