import json
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from loguru import logger
from typing import Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models.frontend_log import FrontendLog

router = APIRouter(prefix="/log", tags=["System Log"])

class LogEntry(BaseModel):
    level: str
    message: str
    timestamp: str
    data: Optional[Any] = None

@router.post("/frontend")
async def log_frontend(entry: LogEntry, db: AsyncSession = Depends(get_db)):
    """
    接收前端发送的日志并写入后端日志文件
    """
    # 构造日志内容，添加 [FRONTEND] 标记
    log_msg = f"[FRONTEND] {entry.message}"
    if entry.data:
        log_msg += f" | Data: {entry.data}"
    
    # 根据级别调用 Loguru
    lvl = entry.level.upper()
    if lvl == "ERROR":
        logger.error(log_msg)
    elif lvl == "WARNING" or lvl == "WARN":
        logger.warning(log_msg)
    elif lvl == "DEBUG":
        logger.debug(log_msg)
    else:
        logger.info(log_msg)

    db_entry = FrontendLog(
        level=lvl,
        message=entry.message,
        data=json.dumps(entry.data, ensure_ascii=False) if entry.data is not None else None,
        client_time=entry.timestamp,
    )
    db.add(db_entry)
    await db.commit()

    return {"status": "ok", "id": db_entry.id}
