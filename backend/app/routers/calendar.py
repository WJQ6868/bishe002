from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from datetime import datetime
from ..database import get_db
from ..models.calendar import CalendarEvent
from ..models.user import User
from ..dependencies.auth import get_current_user
from ..utils.excel import ExcelParser
from pydantic import BaseModel

router = APIRouter(prefix="/calendar", tags=["校历管理"])

# Pydantic Models
class CalendarEventBase(BaseModel):
    title: str
    type: str
    start_date: str
    end_date: str
    location: Optional[str] = None
    related_classes: Optional[str] = None
    description: Optional[str] = None

class CalendarEventCreate(CalendarEventBase):
    pass

class CalendarEventUpdate(CalendarEventBase):
    pass

class CalendarEventOut(CalendarEventBase):
    id: int
    create_time: datetime
    
    class Config:
        orm_mode = True

# API Endpoints

@router.get("/events", response_model=List[CalendarEventOut])
async def get_events(
    start: Optional[str] = None,
    end: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = select(CalendarEvent)
    
    # Simple string comparison for SQLite dates (YYYY-MM-DD)
    if start:
        query = query.where(CalendarEvent.end_date >= start)
    if end:
        query = query.where(CalendarEvent.start_date <= end)
        
    result = await db.execute(query)
    return result.scalars().all()

@router.post("/events", response_model=CalendarEventOut)
async def create_event(
    event: CalendarEventCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admin can create events")
        
    # Validate dates
    if event.start_date > event.end_date:
        raise HTTPException(status_code=400, detail="Start date must be before end date")
        
    db_event = CalendarEvent(**event.dict())
    db.add(db_event)
    await db.commit()
    await db.refresh(db_event)
    return db_event

@router.put("/events/{event_id}", response_model=CalendarEventOut)
async def update_event(
    event_id: int,
    event: CalendarEventUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admin can update events")
        
    result = await db.execute(select(CalendarEvent).where(CalendarEvent.id == event_id))
    db_event = result.scalars().first()
    if not db_event:
        raise HTTPException(status_code=404, detail="Event not found")
        
    for key, value in event.dict().items():
        setattr(db_event, key, value)
        
    await db.commit()
    await db.refresh(db_event)
    return db_event

@router.delete("/events/{event_id}")
async def delete_event(
    event_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admin can delete events")
        
    result = await db.execute(select(CalendarEvent).where(CalendarEvent.id == event_id))
    db_event = result.scalars().first()
    if not db_event:
        raise HTTPException(status_code=404, detail="Event not found")
        
    await db.delete(db_event)
    await db.commit()
    return {"message": "Event deleted"}

@router.post("/import")
async def import_events(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admin can import events")
        
    try:
        events_data = await ExcelParser.parse_calendar_events(file)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
        
    count = 0
    for event_data in events_data:
        db_event = CalendarEvent(**event_data)
        db.add(db_event)
        count += 1
        
    await db.commit()
    return {"message": f"Successfully imported {count} events"}
