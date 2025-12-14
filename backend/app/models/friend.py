"""
好友系统模型
Friend System Models
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, func, UniqueConstraint
from datetime import datetime
import enum

from ..database import Base


class FriendRequestStatus(str, enum.Enum):
    """好友申请状态枚举"""
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class FriendRequest(Base):
    """好友申请表"""
    __tablename__ = "friend_request"

    id = Column(Integer, primary_key=True, autoincrement=True)
    from_user_id = Column(Integer, ForeignKey("sys_users.id"), nullable=False, index=True)
    to_user_id = Column(Integer, ForeignKey("sys_users.id"), nullable=False, index=True)
    message = Column(Text)  # 申请附加消息
    status = Column(String(20), default=FriendRequestStatus.PENDING.value, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<FriendRequest(id={self.id}, from={self.from_user_id}, to={self.to_user_id}, status={self.status})>"


class Friendship(Base):
    """好友关系表
    
    采用规范化设计: user_id_1 < user_id_2
    确保每对好友只有一条记录
    """
    __tablename__ = "friendship"
    __table_args__ = (
        UniqueConstraint('user_id_1', 'user_id_2', name='uq_friendship'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id_1 = Column(Integer, ForeignKey("sys_users.id"), nullable=False, index=True)
    user_id_2 = Column(Integer, ForeignKey("sys_users.id"), nullable=False, index=True)
    created_at = Column(DateTime, server_default=func.now())

    def __repr__(self):
        return f"<Friendship(id={self.id}, user1={self.user_id_1}, user2={self.user_id_2})>"

    @staticmethod
    def normalize_ids(user_id_a: int, user_id_b: int) -> tuple[int, int]:
        """
        规范化用户ID顺序，确保 user_id_1 < user_id_2
        
        Args:
            user_id_a: 用户A的ID
            user_id_b: 用户B的ID
            
        Returns:
            (user_id_1, user_id_2): 规范化后的ID元组
        """
        return (min(user_id_a, user_id_b), max(user_id_a, user_id_b))

    @classmethod
    def create_friendship(cls, user_id_a: int, user_id_b: int):
        """
        创建好友关系实例（自动规范化ID顺序）
        
        Args:
            user_id_a: 用户A的ID
            user_id_b: 用户B的ID
            
        Returns:
            Friendship: 新的好友关系实例
        """
        user_id_1, user_id_2 = cls.normalize_ids(user_id_a, user_id_b)
        return cls(user_id_1=user_id_1, user_id_2=user_id_2)

    def contains_user(self, user_id: int) -> bool:
        """
        检查该好友关系是否包含指定用户
        
        Args:
            user_id: 要检查的用户ID
            
        Returns:
            bool: 是否包含该用户
        """
        return user_id == self.user_id_1 or user_id == self.user_id_2

    def get_friend_id(self, user_id: int) -> int | None:
        """
        获取指定用户的好友ID
        
        Args:
            user_id: 当前用户ID
            
        Returns:
            int | None: 好友的用户ID，如果user_id不在此关系中则返回None
        """
        if user_id == self.user_id_1:
            return self.user_id_2
        elif user_id == self.user_id_2:
            return self.user_id_1
        return None
