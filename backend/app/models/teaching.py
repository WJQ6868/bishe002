"""
教师教学管理 - 数据库模型
包含：点名、作业、调课、工作安排
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Float, Boolean, func
from datetime import datetime
import enum

from ..database import Base


# --- 枚举定义 ---

class AttendanceStatus(str, enum.Enum):
    """签到状态"""
    PRESENT = "已签到"
    LATE = "迟到"
    ABSENT = "未到"
    LEAVE = "请假"


class HomeworkType(str, enum.Enum):
    """作业类型"""
    SUBJECTIVE = "主观题"
    OBJECTIVE = "客观题"
    FILE = "文件提交"


class HomeworkStatus(str, enum.Enum):
    """作业状态"""
    PENDING = "待提交"
    SUBMITTED = "已提交"
    GRADED = "已批改"
    RETURNED = "需重交"
    RESUBMITTED = "待复审"


class AdjustStatus(str, enum.Enum):
    """调课状态"""
    PENDING = "待审核"
    APPROVED = "已通过"
    REJECTED = "已拒绝"


class WorkType(str, enum.Enum):
    """工作类型"""
    CLASS = "上课"
    MEETING = "开会"
    DUTY = "值班"
    OTHER = "其他"


# --- 数据库模型 ---

class Attendance(Base):
    """点名记录表"""
    __tablename__ = "attendance"

    id = Column(Integer, primary_key=True, autoincrement=True)
    course_id = Column(Integer, nullable=False, index=True)
    teacher_id = Column(Integer, nullable=False, index=True)
    student_id = Column(Integer, nullable=False, index=True)
    status = Column(String(20), default=AttendanceStatus.ABSENT.value)
    sign_time = Column(DateTime, nullable=True)
    remark = Column(String(255), nullable=True)
    create_time = Column(DateTime, server_default=func.now())  # 点名发起时间 (批次)


class Homework(Base):
    """作业布置表"""
    __tablename__ = "homework"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(100), nullable=False)
    course_id = Column(Integer, nullable=False, index=True)
    teacher_id = Column(Integer, nullable=False, index=True)
    content = Column(Text, nullable=False)  # 富文本内容
    deadline = Column(DateTime, nullable=False)
    type = Column(String(20), default=HomeworkType.SUBJECTIVE.value)
    score = Column(Integer, default=100)  # 总分
    file_url = Column(Text, nullable=True)  # 附件
    create_time = Column(DateTime, server_default=func.now())


class HomeworkSubmit(Base):
    """作业提交表"""
    __tablename__ = "homework_submit"

    id = Column(Integer, primary_key=True, autoincrement=True)
    homework_id = Column(Integer, nullable=False, index=True)
    student_id = Column(Integer, nullable=False, index=True)
    content = Column(Text, nullable=True)   # 提交内容 (文本)
    file_url = Column(Text, nullable=True)  # 提交文件
    submit_time = Column(DateTime, server_default=func.now())
    status = Column(String(20), default=HomeworkStatus.PENDING.value)
    score = Column(Float, nullable=True)    # 得分
    comment = Column(Text, nullable=True)   # 评语
    update_time = Column(DateTime, onupdate=func.now())


class ClassAdjust(Base):
    """调课申请表"""
    __tablename__ = "class_adjust"

    id = Column(Integer, primary_key=True, autoincrement=True)
    teacher_id = Column(Integer, nullable=False, index=True)
    course_id = Column(Integer, nullable=False)
    old_time = Column(DateTime, nullable=False)
    new_time = Column(DateTime, nullable=False)
    old_classroom = Column(String(50), nullable=True)
    new_classroom = Column(String(50), nullable=True)
    reason = Column(Text, nullable=False)
    file_url = Column(Text, nullable=True)  # 附件
    status = Column(String(20), default=AdjustStatus.PENDING.value)
    create_time = Column(DateTime, server_default=func.now())


class WorkSchedule(Base):
    """教师工作安排表"""
    __tablename__ = "work_schedule"

    id = Column(Integer, primary_key=True, autoincrement=True)
    teacher_id = Column(Integer, nullable=False, index=True)
    time = Column(DateTime, nullable=False)
    content = Column(String(255), nullable=False)
    type = Column(String(20), default=WorkType.OTHER.value)
    remark = Column(String(255), nullable=True)
