"""
好友系统 Pydantic Schemas
Friend System Schemas for Request/Response validation
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class FriendRequestCreate(BaseModel):
    """发送好友申请请求"""
    to_user_id: int = Field(..., description="被申请用户的ID")
    message: Optional[str] = Field(None, max_length=200, description="申请附加消息")


class FriendRequestResponse(BaseModel):
    """好友申请响应"""
    id: int
    from_user_id: int
    to_user_id: int
    message: Optional[str]
    status: str  # pending, accepted, rejected
    created_at: datetime
    updated_at: datetime
    
    # 额外字段（来自关联查询）
    from_user_name: Optional[str] = None
    from_user_username: Optional[str] = None
    to_user_name: Optional[str] = None
    to_user_username: Optional[str] = None

    class Config:
        from_attributes = True


class ProcessFriendRequestRequest(BaseModel):
    """处理好友申请请求"""
    request_id: int = Field(..., description="好友申请ID")
    action: str = Field(..., pattern="^(accept|reject)$", description="操作: accept 或 reject")


class FriendshipResponse(BaseModel):
    """好友关系响应"""
    id: int
    user_id_1: int
    user_id_2: int
    created_at: datetime

    class Config:
        from_attributes = True


class FriendInfo(BaseModel):
    """好友信息（用于好友列表）"""
    user_id: int
    username: str
    name: str
    role: str
    dept: Optional[str] = None
    status: str = "offline"  # online, offline, away
    friendship_id: int
    friend_since: datetime


class FriendSearchResult(BaseModel):
    """搜索用户结果"""
    user_id: int
    username: str
    name: str
    role: str
    dept: Optional[str] = None
    is_friend: bool = False  # 是否已是好友
    has_pending_request: bool = False  # 是否有待处理的申请
    request_direction: Optional[str] = None  # sent: 我发出的, received: 我收到的
