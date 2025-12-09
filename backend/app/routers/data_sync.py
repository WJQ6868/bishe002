from datetime import date, datetime
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..dependencies.auth import get_current_user


ALLOWED_TABLES = {
    "teachers",
    "students",
    "classrooms",
    "chat_message",
    "user_status",
    "leave_apply",
    "attendance",
    "homework",
    "homework_submit",
    "class_adjust",
    "work_schedule",
    "sys_users",
    "courses",
    "student_warnings",
    "grades",
    "course_selections",
    "schedules",
    "calendar_event",
    "service_item",
    "service_apply",
    "cert_links",
    "user_collections",
    "quick_links",
    "admins",
    "user_profiles",
}

router = APIRouter(prefix="/data", tags=["Data Tables"])


def _serialize_value(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def _serialize_row(row) -> Dict[str, Any]:
    return {key: _serialize_value(value) for key, value in row.items()}


def _normalize_names(raw_names: str) -> List[str]:
    if not raw_names:
        return []
    names = []
    for name in raw_names.split(","):
        trimmed = name.strip()
        if not trimmed:
            continue
        if not trimmed.replace("_", "").isalnum():
            continue
        names.append(trimmed)
    return names


@router.get("/tables")
async def get_tables(
    names: str = Query(..., description="Comma-separated table names"),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    requested = _normalize_names(names)
    if not requested:
        raise HTTPException(status_code=400, detail="No valid table names provided")

    tables: Dict[str, List[Dict[str, Any]]] = {}
    for name in requested:
        if name not in ALLOWED_TABLES:
            continue
        stmt = text(f"SELECT * FROM {name}")
        result = await db.execute(stmt)
        rows = result.mappings().all()
        tables[name] = [_serialize_row(row) for row in rows]

    if not tables:
        raise HTTPException(status_code=404, detail="No tables available for the request")

    return {"tables": tables}


@router.get("/table/{table_name}")
async def get_table(
    table_name: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    normalized = _normalize_names(table_name)
    if not normalized:
        raise HTTPException(status_code=400, detail="Invalid table name")
    name = normalized[0]
    if name not in ALLOWED_TABLES:
        raise HTTPException(status_code=404, detail="Table not allowed")

    stmt = text(f"SELECT * FROM {name}")
    result = await db.execute(stmt)
    rows = result.mappings().all()
    return {"table": name, "rows": [_serialize_row(row) for row in rows]}
