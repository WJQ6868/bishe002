"""
Socket.IO 服务管理器
负责实时消息推送、在线状态管理
"""
try:
    import socketio  # 可选依赖：若未安装则降级为空实现以保证服务可启动
except ImportError:
    class _DummyAsyncServer:
        def __init__(self, *args, **kwargs):
            pass
        def event(self, func):
            return func
        async def emit(self, *args, **kwargs):
            return None
    class _DummyASGIApp:
        def __init__(self, *args, **kwargs):
            pass
    socketio = type("socketio", (), {"AsyncServer": _DummyAsyncServer, "ASGIApp": _DummyASGIApp})
from datetime import datetime, timedelta
from typing import Dict, Set
import asyncio
from sqlalchemy import select

# 创建 Socket.IO 服务器 (异步模式)
sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins=['http://localhost:2003', 'http://localhost:5173'],
    cors_credentials=True,
    logger=True,
    engineio_logger=True,
    ping_timeout=60,
    ping_interval=25
)

# 存储在线用户: {user_id: socket_id}
online_users: Dict[int, str] = {}

# 存储用户最后活跃时间
user_last_active: Dict[int, datetime] = {}

# 反向映射: {socket_id: user_id}
socket_to_user: Dict[str, int] = {}


@sio.event
async def connect(sid, environ):
    """客户端连接事件"""
    print(f"[Socket.IO] Client connected: {sid}")


@sio.event
async def disconnect(sid):
    """客户端断开事件"""
    print(f"[Socket.IO] Client disconnected: {sid}")
    # 清理用户在线状态
    if sid in socket_to_user:
        user_id = socket_to_user[sid]
        del online_users[user_id]
        del socket_to_user[sid]
        
        # 持久化状态到 DB
        from ..database import AsyncSessionLocal
        from ..models.message import UserStatus
        from sqlalchemy import select
        from datetime import datetime
        
        async with AsyncSessionLocal() as db:
            stmt = select(UserStatus).where(UserStatus.user_id == user_id)
            result = await db.execute(stmt)
            status_record = result.scalar_one_or_none()
            
            if status_record:
                status_record.status = 'offline'
                status_record.update_time = datetime.now()
            else:
                db.add(UserStatus(user_id=user_id, status='offline'))
            await db.commit()
            
        # 广播用户离线状态
        await sio.emit('user_status_change', {
            'user_id': user_id,
            'status': 'offline'
        })


@sio.event
async def user_login(sid, data):
    """
    用户登录事件
    data: { user_id: int, role: str }
    """
    user_id = data.get('user_id')
    if user_id:
        online_users[user_id] = sid
        socket_to_user[sid] = user_id
        user_last_active[user_id] = datetime.now()
        print(f"[Socket.IO] User {user_id} logged in with socket {sid}")
        
        # 持久化状态到 DB
        from ..database import AsyncSessionLocal
        from ..models.message import UserStatus
        from sqlalchemy import select
        
        async with AsyncSessionLocal() as db:
            stmt = select(UserStatus).where(UserStatus.user_id == user_id)
            result = await db.execute(stmt)
            status_record = result.scalar_one_or_none()
            
            if status_record:
                status_record.status = 'online'
                status_record.update_time = datetime.now()
            else:
                db.add(UserStatus(user_id=user_id, status='online'))
            await db.commit()
        
        # 广播用户上线状态
        await sio.emit('user_status_change', {
            'user_id': user_id,
            'status': 'online'
        })
        
        # 返回当前在线用户列表
        await sio.emit('online_users', {
            'users': list(online_users.keys())
        }, to=sid)


@sio.event
async def send_message(sid, data):
    """
    发送消息事件
    data: { to_id: int, content: str, type: str }
    """
    from_id = socket_to_user.get(sid)
    if not from_id:
        return {'error': '用户未登录'}
    
    to_id = data.get('to_id')
    content = data.get('content')
    msg_type = data.get('type', 'text')
    if not to_id or not content:
        return {'error': '缺少必要的消息参数'}
    
    from ..database import AsyncSessionLocal
    from ..models.message import Message
    from ..models.user import User
    
    async with AsyncSessionLocal() as db:
        user_stmt = select(User).where(User.id == from_id)
        to_stmt = select(User).where(User.id == to_id)
        from_user = (await db.execute(user_stmt)).scalars().first()
        to_user = (await db.execute(to_stmt)).scalars().first()
        if not from_user or not to_user:
            return {'error': '用户不存在'}

        new_msg = Message(
            from_id=from_id,
            from_role=from_user.role,
            to_id=to_id,
            to_role=to_user.role,
            content=content,
            type=msg_type,
            send_time=datetime.now(),
            is_read=0,
        )
        db.add(new_msg)
        await db.commit()
        await db.refresh(new_msg)
        
        # 构造消息对象 (返回给前端)
        message_data = {
            'id': new_msg.id,
            'from_id': new_msg.from_id,
            'to_id': new_msg.to_id,
            'content': new_msg.content,
            'type': new_msg.type,
            'send_time': new_msg.send_time.isoformat(),
            'is_read': False
        }
    
    # 发送给接收者
    if to_id in online_users:
        target_sid = online_users[to_id]
        await sio.emit('new_message', message_data, to=target_sid)
        print(f"[Socket.IO] Message sent from {from_id} to {to_id}")
    
    # 返回消息确认给发送者
    await sio.emit('message_sent', message_data, to=sid)
    
    # 更新最后活跃时间
    user_last_active[from_id] = datetime.now()
    
    return message_data


@sio.event
async def mark_read(sid, data):
    """
    标记消息已读
    data: { message_ids: List[int], from_user_id: int }
    """
    user_id = socket_to_user.get(sid)
    from_user_id = data.get('from_user_id')
    
    if user_id and from_user_id and from_user_id in online_users:
        # 通知消息发送者，消息已被阅读
        target_sid = online_users[from_user_id]
        await sio.emit('messages_read', {
            'reader_id': user_id,
            'message_ids': data.get('message_ids', [])
        }, to=target_sid)


@sio.event
async def heartbeat(sid, data):
    """
    心跳事件，更新用户活跃状态
    """
    user_id = socket_to_user.get(sid)
    if user_id:
        user_last_active[user_id] = datetime.now()


async def check_inactive_users():
    """
    检查不活跃用户，3分钟无操作标记为离开
    """
    while True:
        await asyncio.sleep(60)  # 每分钟检查一次
        now = datetime.now()
        away_threshold = timedelta(minutes=3)
        
        for user_id, last_active in list(user_last_active.items()):
            if user_id in online_users:
                if now - last_active > away_threshold:
                    # 标记为离开状态
                    await sio.emit('user_status_change', {
                        'user_id': user_id,
                        'status': 'away'
                    })


def get_user_status(user_id: int) -> str:
    """获取用户在线状态"""
    if user_id not in online_users:
        return 'offline'
    
    last_active = user_last_active.get(user_id)
    if last_active:
        if datetime.now() - last_active > timedelta(minutes=3):
            return 'away'
    return 'online'


def get_online_user_ids() -> Set[int]:
    """获取所有在线用户ID"""
    return set(online_users.keys())
