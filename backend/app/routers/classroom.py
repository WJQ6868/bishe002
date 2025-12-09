import json
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..database import get_db
from ..dependencies.auth import get_current_admin, get_current_user
from ..models.schedule import Classroom, ClassroomResource, Schedule
from ..schemas.classroom import ClassroomCreate, ClassroomResponse, ClassroomUpdate, ResourceStatus


router = APIRouter(prefix="/classroom", tags=["Classroom Management"])


def _serialize_devices(devices: List[str] | None) -> str | None:
    if not devices:
        return None
    normalized = [str(item).strip() for item in devices if str(item).strip()]
    if not normalized:
        return None
    return json.dumps(normalized, ensure_ascii=False)


def _parse_devices(raw: str | None) -> List[str]:
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return [str(item) for item in parsed if str(item)]
    except json.JSONDecodeError:
        pass
    return [segment.strip() for segment in raw.split(",") if segment.strip()]


def _status_value(status: ResourceStatus | None, fallback: str = "idle") -> str:
    if isinstance(status, ResourceStatus):
        return status.value
    if not status:
        return fallback
    return status


def _classroom_to_response(classroom: Classroom) -> ClassroomResponse:
    resource = classroom.resource
    return ClassroomResponse(
        id=classroom.id,
        name=classroom.name,
        capacity=classroom.capacity,
        is_multimedia=classroom.is_multimedia,
        code=(resource.code if resource and resource.code else f"CLS-{classroom.id:04d}"),
        location=resource.location if resource else None,
        devices=_parse_devices(resource.devices if resource else None),
        status=_status_value(
            resource.status if resource else None,
            fallback="idle",
        ),
        remark=resource.remark if resource else None,
    )


async def _ensure_unique_code(
    db: AsyncSession,
    code: str | None,
    *,
    exclude_classroom_id: int | None = None,
):
    if not code:
        return
    stmt = select(ClassroomResource).where(ClassroomResource.code == code)
    if exclude_classroom_id:
        stmt = stmt.where(ClassroomResource.classroom_id != exclude_classroom_id)
    exists = (await db.execute(stmt)).scalars().first()
    if exists:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="教室编码已存在")


async def _ensure_resource(
    db: AsyncSession,
    classroom: Classroom,
    *,
    suggested_code: str | None = None,
) -> ClassroomResource:
    if classroom.resource:
        return classroom.resource
    resource = ClassroomResource(
        classroom_id=classroom.id,
        code=suggested_code or f"CLS-{classroom.id:04d}",
        status="idle",
    )
    db.add(resource)
    await db.flush()
    classroom.resource = resource
    return resource


@router.get("/list", response_model=List[ClassroomResponse])
async def list_classrooms(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    stmt = select(Classroom).options(selectinload(Classroom.resource)).order_by(Classroom.id)
    result = await db.execute(stmt)
    items = result.scalars().all()
    return [_classroom_to_response(item) for item in items]


@router.post("", response_model=ClassroomResponse, status_code=status.HTTP_201_CREATED)
async def create_classroom(
    payload: ClassroomCreate,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_admin),
):
    existing = (
        await db.execute(
            select(Classroom).where(Classroom.name == payload.name.strip())
        )
    ).scalars().first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="教室名称已存在")

    await _ensure_unique_code(db, payload.code)

    classroom = Classroom(
        name=payload.name.strip(),
        capacity=payload.capacity,
        is_multimedia=payload.is_multimedia,
    )
    db.add(classroom)
    await db.flush()

    resource = ClassroomResource(
        classroom_id=classroom.id,
        code=payload.code or f"CLS-{classroom.id:04d}",
        location=payload.location,
        devices=_serialize_devices(payload.devices),
        status=_status_value(payload.status, fallback="idle"),
        remark=payload.remark,
    )
    db.add(resource)
    classroom.resource = resource
    await db.commit()
    await db.refresh(classroom)

    return _classroom_to_response(classroom)


@router.put("/{classroom_id}", response_model=ClassroomResponse)
async def update_classroom(
    classroom_id: int,
    payload: ClassroomUpdate,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_admin),
):
    stmt = (
        select(Classroom)
        .options(selectinload(Classroom.resource))
        .where(Classroom.id == classroom_id)
    )
    classroom = (await db.execute(stmt)).scalars().first()
    if not classroom:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="教室不存在")

    update_data = payload.dict(exclude_unset=True)
    if "name" in update_data:
        conflict = (
            await db.execute(
                select(Classroom).where(
                    Classroom.name == update_data["name"].strip(),
                    Classroom.id != classroom_id,
                )
            )
        ).scalars().first()
        if conflict:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="教室名称已存在")
        classroom.name = update_data["name"].strip()

    if "capacity" in update_data:
        classroom.capacity = update_data["capacity"]

    if "is_multimedia" in update_data:
        classroom.is_multimedia = bool(update_data["is_multimedia"])

    resource = await _ensure_resource(
        db, classroom, suggested_code=update_data.get("code")
    )

    if "code" in update_data:
        await _ensure_unique_code(
            db, update_data["code"], exclude_classroom_id=classroom.id
        )
        resource.code = update_data["code"]

    if "location" in update_data:
        resource.location = update_data["location"]

    if "devices" in update_data:
        resource.devices = _serialize_devices(update_data["devices"])

    if "status" in update_data and update_data["status"]:
        resource.status = _status_value(update_data["status"], fallback=resource.status or "idle")

    if "remark" in update_data:
        resource.remark = update_data["remark"]

    await db.commit()
    await db.refresh(classroom)
    return _classroom_to_response(classroom)


@router.delete("/{classroom_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_classroom(
    classroom_id: int,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_admin),
):
    classroom = (
        await db.execute(select(Classroom).where(Classroom.id == classroom_id))
    ).scalars().first()
    if not classroom:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="教室不存在")

    used_count = (
        await db.execute(
            select(func.count(Schedule.id)).where(Schedule.classroom_id == classroom_id)
        )
    ).scalar()
    if used_count and used_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="教室已被排课使用，无法删除",
        )

    await db.delete(classroom)
    await db.commit()
    return None
