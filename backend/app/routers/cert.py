from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, desc
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from ..database import get_db
from ..models.cert import CertLink, UserCollection
from ..models.user import User
from ..dependencies.auth import get_current_user, get_current_admin
from ..services.socket_manager import sio

router = APIRouter(
    prefix="/cert",
    tags=["Certificates"],
    responses={404: {"description": "Not found"}},
)

# Pydantic Schemas
class CertLinkBase(BaseModel):
    name: str
    category: str
    icon: Optional[str] = None
    url: str
    description: Optional[str] = None
    is_hot: bool = False
    is_official: bool = True

class CertLinkCreate(CertLinkBase):
    pass

class CertLinkOut(CertLinkBase):
    id: int
    click_count: int
    create_time: datetime
    is_collected: Optional[bool] = False  # For user context

    class Config:
        from_attributes = True

class CollectionCreate(BaseModel):
    link_id: int

# Routes

@router.get("/list", response_model=List[CertLinkOut])
async def get_cert_links(
    category: Optional[str] = None,
    keyword: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    query = select(CertLink)
    
    if category and category != "all":
        query = query.where(CertLink.category == category)
    
    if keyword:
        query = query.where(CertLink.name.like(f"%{keyword}%"))
    
    # Order by hot (priority) and then id
    query = query.order_by(desc(CertLink.is_hot), CertLink.id)
    
    result = await db.execute(query)
    links = result.scalars().all()
    
    # Check collection status for current user
    user_collections_query = select(UserCollection.link_id).where(UserCollection.user_id == current_user.id)
    uc_result = await db.execute(user_collections_query)
    collected_ids = set(uc_result.scalars().all())
    
    response_links = []
    for link in links:
        link_out = CertLinkOut.from_orm(link)
        link_out.is_collected = link.id in collected_ids
        response_links.append(link_out)
        
    return response_links

@router.post("/collect")
async def toggle_collection(
    data: CollectionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Check if already collected
    query = select(UserCollection).where(
        UserCollection.user_id == current_user.id,
        UserCollection.link_id == data.link_id
    )
    result = await db.execute(query)
    collection = result.scalars().first()
    
    if collection:
        # Uncollect
        await db.delete(collection)
        await db.commit()
        return {"status": "uncollected"}
    else:
        # Collect
        new_collection = UserCollection(user_id=current_user.id, link_id=data.link_id)
        db.add(new_collection)
        await db.commit()
        return {"status": "collected"}

@router.get("/collection/list", response_model=List[CertLinkOut])
async def get_my_collections(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    query = select(CertLink).join(UserCollection).where(UserCollection.user_id == current_user.id)
    result = await db.execute(query)
    links = result.scalars().all()
    
    response_links = []
    for link in links:
        link_out = CertLinkOut.from_orm(link)
        link_out.is_collected = True
        response_links.append(link_out)
        
    return response_links

# Admin Routes

@router.post("/create", response_model=CertLinkOut)
async def create_cert_link(
    link: CertLinkCreate,
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    new_link = CertLink(**link.dict())
    db.add(new_link)
    await db.commit()
    await db.refresh(new_link)
    try:
        await sio.emit('cert_links_updated', {
            'action': 'create',
            'id': new_link.id
        })
    except Exception:
        pass
    return new_link

@router.put("/update/{link_id}", response_model=CertLinkOut)
async def update_cert_link(
    link_id: int,
    link_update: CertLinkCreate,
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    query = select(CertLink).where(CertLink.id == link_id)
    result = await db.execute(query)
    link = result.scalars().first()
    
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")
    
    for key, value in link_update.dict().items():
        setattr(link, key, value)
    
    await db.commit()
    await db.refresh(link)
    try:
        await sio.emit('cert_links_updated', {
            'action': 'update',
            'id': link.id
        })
    except Exception:
        pass
    return link

@router.delete("/delete/{link_id}")
async def delete_cert_link(
    link_id: int,
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    query = select(CertLink).where(CertLink.id == link_id)
    result = await db.execute(query)
    link = result.scalars().first()
    
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")
    
    # Delete associated collections first (cascade usually handles this but being safe)
    await db.execute(select(UserCollection).where(UserCollection.link_id == link_id).execution_options(synchronize_session=False))
    
    await db.delete(link)
    await db.commit()
    try:
        await sio.emit('cert_links_updated', {
            'action': 'delete',
            'id': link_id
        })
    except Exception:
        pass
    return {"status": "deleted"}

@router.post("/click/{link_id}")
async def record_click(
    link_id: int,
    db: AsyncSession = Depends(get_db)
):
    query = select(CertLink).where(CertLink.id == link_id)
    result = await db.execute(query)
    link = result.scalars().first()
    
    if link:
        link.click_count += 1
        await db.commit()
    
    return {"status": "ok"}
