"""
请假管理 - 数据库模型
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, func
from datetime import datetime
import enum

from ..database import Base


class LeaveType(str, enum.Enum):
    """请假类型"""
    SICK = "病假"
    PERSONAL = "事假"
    OTHER = "其他"


class LeaveStatus(str, enum.Enum):
    """请假状态"""
    PENDING = "pending"     # 待审核
    APPROVED = "approved"   # 已通过
    REJECTED = "rejected"   # 已拒绝
    RECALLED = "recalled"   # 已撤回


class LeaveApply(Base):
    """请假申请表"""
    __tablename__ = "leave_apply"

    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(Integer, nullable=False, index=True)
    course_id = Column(Integer, nullable=False, index=True)
    teacher_id = Column(Integer, nullable=False, index=True)
    type = Column(String(20), nullable=False)  # 病假/事假/其他
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    reason = Column(Text, nullable=False)
    file_url = Column(Text, nullable=True)  # 证明材料路径
    status = Column(String(20), default=LeaveStatus.PENDING.value, nullable=False)
    opinion = Column(Text, nullable=True)   # 审批意见
    approve_time = Column(DateTime, nullable=True)
    create_time = Column(DateTime, server_default=func.now())
    
    # 外键约束 (可选，SQLite 默认不强制)
    # student = relationship("User", foreign_keys=[student_id])
    # course = relationship("Course", foreign_keys=[course_id])
    # teacher = relationship("User", foreign_keys=[teacher_id])
