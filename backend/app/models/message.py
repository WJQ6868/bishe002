"""
即时通讯 - 消息与用户状态模型
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, func
from datetime import datetime
import enum

from ..database import Base


class MessageType(str, enum.Enum):
    """消息类型"""
    TEXT = "text"
    IMAGE = "image"
    EMOJI = "emoji"


class UserStatusEnum(str, enum.Enum):
    """用户状态枚举"""
    ONLINE = "online"
    OFFLINE = "offline"
    AWAY = "away"


def get_conversation_id(user1_id: int, user2_id: int) -> str:
    """生成会话ID (小ID_大ID)"""
    return f"{min(user1_id, user2_id)}_{max(user1_id, user2_id)}"



class Message(Base):
    """消息表 - 存储师生聊天记录"""
    __tablename__ = "chat_message"

    id = Column(Integer, primary_key=True, autoincrement=True)
    from_id = Column(Integer, nullable=False, index=True)  # 发送者ID
    from_role = Column(String(20), nullable=False)         # 发送者角色 (student/teacher)
    to_id = Column(Integer, nullable=False, index=True)    # 接收者ID
    to_role = Column(String(20), nullable=False)           # 接收者角色 (student/teacher)
    content = Column(Text, nullable=False)                 # 消息内容
    type = Column(String(20), default=MessageType.TEXT.value)  # 消息类型
    send_time = Column(DateTime, server_default=func.now()) # 发送时间 (SQLite TIMESTAMP)
    is_read = Column(Integer, default=0)                   # 0-未读，1-已读 (SQLite适配)
    
    # 辅助字段，用于应用层逻辑，不一定非要存库，但为了查询方便可以保留 conversation_id 如果需要
    # 但根据用户给出的 SQL，没有 conversation_id，我将移除它以严格匹配 SQL，
    # 或者保留它作为 SQLAlchemy 层的辅助（如果数据库允许额外字段）。
    # 用户给的 SQL 没有 conversation_id，为了严格匹配，我先移除，
    # 但 conversation_id 在查询历史记录时很有用。
    # 用户的 SQL 是 "CREATE TABLE IF NOT EXISTS chat_message ...", 
    # 如果我添加了 conversation_id，SQLAlchemy 会尝试创建它。
    # 为了保证功能（之前的代码用了 conversation_id），我建议保留它，
    # 除非用户明确禁止。用户只列出了核心字段。
    # 为了稳妥，我保留 conversation_id 但使其可选，或者通过计算得出。
    # 之前的实现用了 conversation_id，如果去掉，routers/message.py 需要修改查询逻辑。
    # 让我们看看 routers/message.py 的查询逻辑：
    # stmt = select(Message).where(or_(and_(Message.from_id == from_id, Message.to_id == to_id), ...))
    # 现在的 router 已经改成了双向查询，不再依赖 conversation_id。
    # 所以我可以安全地移除 conversation_id。
    
    # FOREIGN KEY 约束
    # from_user = relationship("User", foreign_keys=[from_id])
    # to_user = relationship("User", foreign_keys=[to_id])


class UserStatus(Base):
    """用户在线状态表"""
    __tablename__ = "user_status"

    user_id = Column(Integer, primary_key=True, index=True) # 主键
    status = Column(String(20), default="offline", nullable=False) # online/offline/away
    update_time = Column(DateTime, server_default=func.now(), onupdate=func.now()) # 更新时间
    
    # FOREIGN KEY (user_id) REFERENCES user(id)
