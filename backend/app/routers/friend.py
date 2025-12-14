"""
好友系统 API 路由
Friend System API Routes
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_, func, desc
from typing import List
from datetime import datetime

from ..database import get_db
from ..models.friend import FriendRequest, Friendship, FriendRequestStatus
from ..models.user import User, UserProfile
from ..models.message import UserStatus
from ..schemas.friend import (
    FriendRequestCreate, FriendRequestResponse, 
    ProcessFriendRequestRequest, FriendInfo, FriendSearchResult
)
from ..dependencies.auth import get_current_user
from ..services.socket_manager import sio, online_users

router = APIRouter(tags=["好友管理"])


def success_response(data=None, message="success"):
    """统一成功响应格式"""
    return {"code": 200, "message": message, "data": data}


@router.get("/friend/search", response_model=None)
async def search_users(
    keyword: str = Query(..., min_length=1, description="搜索关键词（姓名/学号/工号）"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    搜索用户
    - 支持按姓名、学号、工号搜索
    - 返回搜索结果及好友状态
    """
    # 搜索用户（排除自己）
    stmt = (
        select(User, UserProfile)
        .outerjoin(UserProfile, UserProfile.user_id == User.id)
        .where(
            and_(
                User.id != current_user.id,
                or_(
                    User.username.like(f"%{keyword}%"),
                    UserProfile.name.like(f"%{keyword}%")
                )
            )
        )
        .limit(20)  # 限制结果数量
    )
    
    result = await db.execute(stmt)
    users = result.all()
    
    if not users:
        return success_response({"results": []})
    
    user_ids = [user.id for user, _ in users]
    
    # 查询好友关系
    friendship_stmt = select(Friendship).where(
        or_(
            and_(Friendship.user_id_1 == current_user.id, Friendship.user_id_2.in_(user_ids)),
            and_(Friendship.user_id_2 == current_user.id, Friendship.user_id_1.in_(user_ids))
        )
    )
    friendships = await db.execute(friendship_stmt)
    friend_ids = set()
    for friendship in friendships.scalars():
        friend_id = friendship.get_friend_id(current_user.id)
        if friend_id:
            friend_ids.add(friend_id)
    
    # 查询待处理的好友申请
    request_stmt = select(FriendRequest).where(
        and_(
            or_(
                and_(FriendRequest.from_user_id == current_user.id, FriendRequest.to_user_id.in_(user_ids)),
                and_(FriendRequest.to_user_id == current_user.id, FriendRequest.from_user_id.in_(user_ids))
            ),
            FriendRequest.status == FriendRequestStatus.PENDING.value
        )
    )
    requests = await db.execute(request_stmt)
    pending_requests = {}
    for req in requests.scalars():
        if req.from_user_id == current_user.id:
            pending_requests[req.to_user_id] = "sent"
        else:
            pending_requests[req.from_user_id] = "received"
    
    # 构建响应
    results = []
    for user, profile in users:
        results.append(FriendSearchResult(
            user_id=user.id,
            username=user.username,
            name=profile.name if profile else user.username,
            role=user.role,
            dept=profile.dept if profile else None,
            is_friend=user.id in friend_ids,
            has_pending_request=user.id in pending_requests,
            request_direction=pending_requests.get(user.id)
        ).model_dump())
    
    return success_response({"results": results})


@router.post("/friend/request/send", response_model=None)
async def send_friend_request(
    req: FriendRequestCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    发送好友申请
    - 检查是否已是好友
    - 检查是否已有待处理的申请
    """
    # 不能向自己发送申请
    if req.to_user_id == current_user.id:
        raise HTTPException(status_code=400, detail="不能向自己发送好友申请")
    
    # 检查目标用户是否存在
    target_stmt = select(User).where(User.id == req.to_user_id)
    target_result = await db.execute(target_stmt)
    target_user = target_result.scalars().first()
    if not target_user:
        raise HTTPException(status_code=404, detail="目标用户不存在")
    
    # 检查是否已是好友
    user_id_1, user_id_2 = Friendship.normalize_ids(current_user.id, req.to_user_id)
    friendship_stmt = select(Friendship).where(
        and_(Friendship.user_id_1 == user_id_1, Friendship.user_id_2 == user_id_2)
    )
    existing_friendship = await db.execute(friendship_stmt)
    if existing_friendship.scalars().first():
        raise HTTPException(status_code=400, detail="已经是好友了")
    
    # 检查是否已有待处理的申请（双向检查）
    pending_stmt = select(FriendRequest).where(
        and_(
            or_(
                and_(FriendRequest.from_user_id == current_user.id, FriendRequest.to_user_id == req.to_user_id),
                and_(FriendRequest.from_user_id == req.to_user_id, FriendRequest.to_user_id == current_user.id)
            ),
            FriendRequest.status == FriendRequestStatus.PENDING.value
        )
    )
    pending_result = await db.execute(pending_stmt)
    if pending_result.scalars().first():
        raise HTTPException(status_code=400, detail="已有待处理的好友申请")
    
    # 创建好友申请
    friend_request = FriendRequest(
        from_user_id=current_user.id,
        to_user_id=req.to_user_id,
        message=req.message,
        status=FriendRequestStatus.PENDING.value
    )
    db.add(friend_request)
    await db.commit()
    await db.refresh(friend_request)
    
    # WebSocket 实时通知
    if req.to_user_id in online_users:
        # 获取发送者姓名
        profile_stmt = select(UserProfile).where(UserProfile.user_id == current_user.id)
        profile_result = await db.execute(profile_stmt)
        profile = profile_result.scalars().first()
        
        target_sid = online_users[req.to_user_id]
        await sio.emit('friend_request_received', {
            'request_id': friend_request.id,
            'from_user_id': current_user.id,
            'from_user_name': profile.name if profile else current_user.username,
            'from_user_username': current_user.username,
            'message': req.message,
            'created_at': friend_request.created_at.isoformat()
        }, to=target_sid)
    
    return success_response(FriendRequestResponse.model_validate(friend_request).model_dump(), 
                           message="好友申请已发送")


@router.get("/friend/request/list", response_model=None)
async def get_received_friend_requests(
    status_filter: str = Query("pending", description="状态筛选: pending, all"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取收到的好友申请列表
    """
    stmt = select(FriendRequest, User, UserProfile).join(
        User, User.id == FriendRequest.from_user_id
    ).outerjoin(
        UserProfile, UserProfile.user_id == User.id
    ).where(
        FriendRequest.to_user_id == current_user.id
    )
    
    if status_filter == "pending":
        stmt = stmt.where(FriendRequest.status == FriendRequestStatus.PENDING.value)
    
    stmt = stmt.order_by(desc(FriendRequest.created_at))
    
    result = await db.execute(stmt)
    requests = result.all()
    
    request_list = []
    for req, user, profile in requests:
        response = FriendRequestResponse.model_validate(req).model_dump()
        response['from_user_name'] = profile.name if profile else user.username
        response['from_user_username'] = user.username
        request_list.append(response)
    
    return success_response({"requests": request_list, "total": len(request_list)})


@router.get("/friend/request/sent", response_model=None)
async def get_sent_friend_requests(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取发出的好友申请列表
    """
    stmt = select(FriendRequest, User, UserProfile).join(
        User, User.id == FriendRequest.to_user_id
    ).outerjoin(
        UserProfile, UserProfile.user_id == User.id
    ).where(
        FriendRequest.from_user_id == current_user.id
    ).order_by(desc(FriendRequest.created_at))
    
    result = await db.execute(stmt)
    requests = result.all()
    
    request_list = []
    for req, user, profile in requests:
        response = FriendRequestResponse.model_validate(req).model_dump()
        response['to_user_name'] = profile.name if profile else user.username
        response['to_user_username'] = user.username
        request_list.append(response)
    
    return success_response({"requests": request_list, "total": len(request_list)})


@router.post("/friend/request/process", response_model=None)
async def process_friend_request(
    req: ProcessFriendRequestRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    处理好友申请（接受/拒绝）
    - 只能处理发给自己的申请
    - 接受时自动创建好友关系
    """
    # 查询申请
    stmt = select(FriendRequest).where(FriendRequest.id == req.request_id)
    result = await db.execute(stmt)
    friend_request = result.scalars().first()
    
    if not friend_request:
        raise HTTPException(status_code=404, detail="好友申请不存在")
    
    # 权限校验：只能处理发给自己的申请
    if friend_request.to_user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权处理此申请")
    
    # 状态校验：只能处理待处理的申请
    if friend_request.status != FriendRequestStatus.PENDING.value:
        raise HTTPException(status_code=400, detail="该申请已被处理")
    
    # 更新申请状态
    if req.action == "accept":
        friend_request.status = FriendRequestStatus.ACCEPTED.value
        
        # 创建好友关系
        friendship = Friendship.create_friendship(current_user.id, friend_request.from_user_id)
        db.add(friendship)
        
        message = "已接受好友申请"
        
        # WebSocket 通知申请发起者
        if friend_request.from_user_id in online_users:
            # 获取当前用户姓名
            profile_stmt = select(UserProfile).where(UserProfile.user_id == current_user.id)
            profile_result = await db.execute(profile_stmt)
            profile = profile_result.scalars().first()
            
            requester_sid = online_users[friend_request.from_user_id]
            await sio.emit('friend_request_processed', {
                'request_id': friend_request.id,
                'status': 'accepted',
                'user_id': current_user.id,
                'user_name': profile.name if profile else current_user.username
            }, to=requester_sid)
            
            # 通知双方好友添加成功
            await sio.emit('friend_added', {
                'friend_id': current_user.id,
                'friend_name': profile.name if profile else current_user.username
            }, to=requester_sid)
        
        # 通知当前用户
        if current_user.id in online_users:
            from_profile_stmt = select(UserProfile).where(UserProfile.user_id == friend_request.from_user_id)
            from_profile_result = await db.execute(from_profile_stmt)
            from_profile = from_profile_result.scalars().first()
            
            current_sid = online_users[current_user.id]
            await sio.emit('friend_added', {
                'friend_id': friend_request.from_user_id,
                'friend_name': from_profile.name if from_profile else str(friend_request.from_user_id)
            }, to=current_sid)
        
    else:  # reject
        friend_request.status = FriendRequestStatus.REJECTED.value
        message = "已拒绝好友申请"
        
        # WebSocket 通知
        if friend_request.from_user_id in online_users:
            requester_sid = online_users[friend_request.from_user_id]
            await sio.emit('friend_request_processed', {
                'request_id': friend_request.id,
                'status': 'rejected',
                'user_id': current_user.id
            }, to=requester_sid)
    
    friend_request.updated_at = datetime.now()
    await db.commit()
    
    return success_response(message=message)


@router.get("/friend/list", response_model=None)
async def get_friend_list(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取好友列表
    - 返回好友详细信息和在线状态
    """
    # 查询好友关系
    stmt = select(Friendship).where(
        or_(
            Friendship.user_id_1 == current_user.id,
            Friendship.user_id_2 == current_user.id
        )
    )
    result = await db.execute(stmt)
    friendships = result.scalars().all()
    
    if not friendships:
        return success_response({"friends": []})
    
    # 获取所有好友ID
    friend_ids = []
    friendship_map = {}
    for friendship in friendships:
        friend_id = friendship.get_friend_id(current_user.id)
        if friend_id:
            friend_ids.append(friend_id)
            friendship_map[friend_id] = friendship
    
    # 查询好友用户信息
    user_stmt = select(User, UserProfile).outerjoin(
        UserProfile, UserProfile.user_id == User.id
    ).where(User.id.in_(friend_ids))
    
    user_result = await db.execute(user_stmt)
    users = user_result.all()
    
    # 查询在线状态
    status_stmt = select(UserStatus).where(UserStatus.user_id.in_(friend_ids))
    status_result = await db.execute(status_stmt)
    status_map = {s.user_id: s.status for s in status_result.scalars()}
    
    # 构建好友列表
    friends = []
    for user, profile in users:
        friendship = friendship_map[user.id]
        friends.append(FriendInfo(
            user_id=user.id,
            username=user.username,
            name=profile.name if profile else user.username,
            role=user.role,
            dept=profile.dept if profile else None,
            status=status_map.get(user.id, "offline"),
            friendship_id=friendship.id,
            friend_since=friendship.created_at
        ).model_dump())
    
    # 按添加时间倒序
    friends.sort(key=lambda x: x['friend_since'], reverse=True)
    
    return success_response({"friends": friends, "total": len(friends)})


@router.delete("/friend/delete/{friend_id}", response_model=None)
async def delete_friend(
    friend_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    删除好友
    - 删除好友关系记录
    """
    # 查询好友关系
    user_id_1, user_id_2 = Friendship.normalize_ids(current_user.id, friend_id)
    stmt = select(Friendship).where(
        and_(Friendship.user_id_1 == user_id_1, Friendship.user_id_2 == user_id_2)
    )
    result = await db.execute(stmt)
    friendship = result.scalars().first()
    
    if not friendship:
        raise HTTPException(status_code=404, detail="好友关系不存在")
    
    # 删除关系
    await db.delete(friendship)
    await db.commit()
    
    # WebSocket 通知对方
    if friend_id in online_users:
        target_sid = online_users[friend_id]
        await sio.emit('friend_deleted', {
            'user_id': current_user.id
        }, to=target_sid)
    
    return success_response(message="已删除好友")
