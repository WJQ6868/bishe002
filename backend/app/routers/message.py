"""
即时通讯 - 消息 API 路由
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_, func, desc, update
from typing import Dict, Set
from datetime import datetime, timedelta

from ..database import get_db
from ..models.message import Message, UserStatus, MessageType
from ..models.user import User, UserProfile
from ..models.student import CourseSelection, Student
from ..models.course import Course, Teacher
from ..schemas.message import (
    ChatMessageCreate, ChatMessageResponse, ChatHistoryResponse,
    UnreadCountResponse, MarkReadRequest, UserStatusUpdate
)
from ..dependencies.auth import get_current_user
from ..dependencies.permissions import check_chat_permission
from ..services.socket_manager import sio, online_users

router = APIRouter(tags=["即时通讯"])

# 内存缓存作为 Redis 的替代 (如果 Redis 不可用)
status_cache: Dict[int, Dict] = {}

def success_response(data=None, message="success"):
    return {"code": 200, "message": message, "data": data}

@router.post("/chat/send", response_model=None)
async def send_message(
    msg: ChatMessageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    发送消息
    - 校验 JWT
    - 校验师生关系权限
    """
    # 1. 校验发送者身份 (确保 from_id 是当前用户)
    if msg.from_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无法代表其他用户发送消息"
        )
        
    # 2. 校验权限 (师生关系)
    await check_chat_permission(current_user, msg.to_id, db)

    # 3. 确定角色 (基于当前用户和目标用户)
    from_role = current_user.role
    
    # 查询目标用户以获取角色
    stmt = select(User).where(User.id == msg.to_id)
    result = await db.execute(stmt)
    target_user = result.scalars().first()
    if not target_user:
        raise HTTPException(status_code=404, detail="Target user not found")
    to_role = target_user.role

    new_msg = Message(
        from_id=msg.from_id,
        from_role=from_role,
        to_id=msg.to_id,
        to_role=to_role,
        content=msg.content,
        type=msg.type.value,
        send_time=datetime.now(),
        is_read=0
    )
    
    db.add(new_msg)
    await db.commit()
    await db.refresh(new_msg)
    
    # Socket.IO 推送
    if msg.to_id in online_users:
        target_sid = online_users[msg.to_id]
        await sio.emit('new_message', {
            'id': new_msg.id,
            'from_id': new_msg.from_id,
            'to_id': new_msg.to_id,
            'content': new_msg.content,
            'type': new_msg.type,
            'send_time': new_msg.send_time.isoformat(),
            'is_read': False
        }, to=target_sid)
    
    return success_response(ChatMessageResponse.model_validate(new_msg).model_dump())


@router.get("/chat/history", response_model=None)
async def get_chat_history(
    to_id: int = Query(..., description="对方用户ID"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取聊天记录 (分页)
    """
    from_id = current_user.id
    
    # 查询两个用户之间的所有消息 (双向)
    stmt = select(Message).where(
        or_(
            and_(Message.from_id == from_id, Message.to_id == to_id),
            and_(Message.from_id == to_id, Message.to_id == from_id)
        )
    ).order_by(desc(Message.send_time))
    
    # 计算总数
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0
    
    # 分页查询
    stmt = stmt.offset((page - 1) * size).limit(size)
    result = await db.execute(stmt)
    messages = result.scalars().all()
    
    # 注意：通常聊天记录是倒序查（最新的在前），前端展示可能需要正序
    # 这里保持倒序返回，前端 reverse 或者后端 reverse
    # 为了符合一般 API 习惯，列表返回最新的在前
    
    data = ChatHistoryResponse(
        total=total,
        page=page,
        size=size,
        list=[ChatMessageResponse.model_validate(m) for m in messages]
    ).model_dump()
    
    return success_response(data)


@router.get("/chat/unread", response_model=None)
async def get_unread_count(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取未读消息数
    """
    user_id = current_user.id
    
    # 查询发给当前用户且未读的消息
    stmt = select(Message.from_id, func.count(Message.id)).where(
        and_(
            Message.to_id == user_id,
            Message.is_read == 0
        )
    ).group_by(Message.from_id)
    
    result = await db.execute(stmt)
    rows = result.all()
    
    details = {row[0]: row[1] for row in rows}
    total_unread = sum(details.values())
    
    data = UnreadCountResponse(
        user_id=user_id,
        total_unread=total_unread,
        details=details
    ).model_dump()
    
    return success_response(data)


@router.post("/chat/read", response_model=None)
async def mark_read(
    req: MarkReadRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    标记消息已读
    """
    user_id = current_user.id
    
    # 校验：只能标记发给自己的消息为已读
    if req.user_id != user_id:
         raise HTTPException(status_code=403, detail="User ID mismatch")

    # 将对方发给当前用户的所有未读消息标记为已读
    stmt = update(Message).where(
        and_(
            Message.from_id == req.target_id,
            Message.to_id == user_id,
            Message.is_read == 0
        )
    ).values(is_read=1)
    
    await db.execute(stmt)
    await db.commit()
    
    return success_response()


@router.get("/chat/contacts", response_model=None)
async def get_chat_contacts(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    基于选课关系返回可聊天联系人列表
    """
    usernames: Set[str] = set()

    if current_user.role == "student":
        stmt = (
            select(Teacher.id)
            .join(Course, Course.teacher_id == Teacher.id)
            .join(CourseSelection, CourseSelection.course_id == Course.id)
            .where(CourseSelection.student_id == current_user.username)
        )
        result = await db.execute(stmt)
        usernames.update(row[0] for row in result)
    elif current_user.role == "teacher":
        stmt = (
            select(CourseSelection.student_id)
            .join(Course, Course.id == CourseSelection.course_id)
            .where(Course.teacher_id == current_user.username)
        )
        result = await db.execute(stmt)
        usernames.update(row[0] for row in result)
    else:
        # 管理员或其他人可以看到所有师生
        stmt = select(User.username).where(User.role.in_(["teacher", "student"]))
        result = await db.execute(stmt)
        usernames.update(row[0] for row in result)

    if not usernames:
        return success_response({"contacts": []})

    user_stmt = (
        select(User, UserProfile)
        .outerjoin(UserProfile, UserProfile.user_id == User.id)
        .where(User.username.in_(usernames))
    )
    rows = await db.execute(user_stmt)
    contact_entries = rows.all()
    contact_ids = [user.id for user, _ in contact_entries]

    unread_map: Dict[int, int] = {}
    if contact_ids:
        unread_stmt = (
            select(Message.from_id, func.count(Message.id))
            .where(
                and_(
                    Message.to_id == current_user.id,
                    Message.from_id.in_(contact_ids),
                    Message.is_read == 0,
                )
            )
            .group_by(Message.from_id)
        )
        unread_rows = await db.execute(unread_stmt)
        unread_map = {row[0]: row[1] for row in unread_rows}

    last_map: Dict[int, Dict[str, datetime]] = {}
    for contact_id in contact_ids:
        last_stmt = (
            select(Message)
            .where(
                or_(
                    and_(Message.from_id == current_user.id, Message.to_id == contact_id),
                    and_(Message.from_id == contact_id, Message.to_id == current_user.id),
                )
            )
            .order_by(desc(Message.send_time))
            .limit(1)
        )
        last_res = await db.execute(last_stmt)
        last_msg = last_res.scalars().first()
        if last_msg:
            last_map[contact_id] = {
                "content": last_msg.content,
                "time": last_msg.send_time,
            }
    
    # 获取在线状态
    status_stmt = select(UserStatus).where(UserStatus.user_id.in_(contact_ids))
    status_res = await db.execute(status_stmt)
    status_map = {s.user_id: s.status for s in status_res.scalars().all()}

    contacts_payload = []
    for user, profile in contact_entries:
        last_info = last_map.get(user.id)
        contacts_payload.append(
            {
                "user_id": user.id,
                "username": user.username,
                "name": profile.name if profile and profile.name else user.username,
                "role": user.role,
                "unread": unread_map.get(user.id, 0),
                "last_message": last_info["content"] if last_info else None,
                "last_time": last_info["time"].isoformat() if last_info else None,
                "status": status_map.get(user.id, "offline")
            }
        )

    contacts_payload.sort(key=lambda c: c["last_time"] or "", reverse=True)
    return success_response({"contacts": contacts_payload})


@router.post("/user/status", response_model=None)
async def update_user_status(
    req: UserStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    更新用户在线状态
    - Redis 缓存优先 (这里用内存模拟)
    - SQLite 持久化备份
    """
    if req.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Cannot update other user's status")

    # 1. 更新缓存 (模拟 Redis 3分钟过期)
    status_cache[req.user_id] = {
        "status": req.status,
        "update_time": datetime.now(),
        "expire": datetime.now() + timedelta(minutes=3)
    }
    
    # 2. 更新 SQLite (持久化)
    stmt = select(UserStatus).where(UserStatus.user_id == req.user_id)
    result = await db.execute(stmt)
    status_record = result.scalar_one_or_none()
    
    if status_record:
        status_record.status = req.status
        status_record.update_time = datetime.now()
    else:
        status_record = UserStatus(
            user_id=req.user_id,
            status=req.status
        )
        db.add(status_record)
        
    await db.commit()
    
    # 3. 广播状态变更 (通过 Socket.IO)
    await sio.emit('user_status_change', {
        'user_id': req.user_id,
        'status': req.status
    })
    
    return success_response({"status": req.status})
