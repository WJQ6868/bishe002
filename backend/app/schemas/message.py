"""
即时通讯 - Pydantic 模型
"""
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List, Dict
from enum import Enum


class MessageType(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    EMOJI = "emoji"


class ChatMessageCreate(BaseModel):
    """发送消息请求"""
    from_id: int
    to_id: int
    content: str
    type: MessageType = MessageType.TEXT
    # 角色信息由后端根据 ID 自动判断或由前端传递，这里为了接口灵活性暂不强制
    # 实际业务中通常从 token 获取 from_id 和 role


class ChatMessageResponse(BaseModel):
    """消息响应"""
    id: int
    from_id: int
    from_role: str
    to_id: int
    to_role: str
    content: str
    type: str
    send_time: datetime
    is_read: int

    class Config:
        from_attributes = True


class ChatHistoryResponse(BaseModel):
    """历史记录响应"""
    total: int
    page: int
    size: int
    list: List[ChatMessageResponse]


class UnreadCountResponse(BaseModel):
    """未读数响应"""
    user_id: int
    total_unread: int
    details: Dict[int, int]  # {sender_id: count}


class MarkReadRequest(BaseModel):
    """标记已读请求"""
    user_id: int      # 当前用户ID
    target_id: int    # 对方ID (标记与该用户的聊天为已读)


class UserStatusUpdate(BaseModel):
    """更新状态请求"""
    user_id: int
    status: str  # online/offline/away
