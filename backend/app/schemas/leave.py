"""
请假管理 - Pydantic 模型
"""
from pydantic import BaseModel, validator
from datetime import datetime
from typing import Optional, List
from enum import Enum


class LeaveType(str, Enum):
    SICK = "病假"
    PERSONAL = "事假"
    OTHER = "其他"


class LeaveStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    RECALLED = "recalled"


class LeaveCreate(BaseModel):
    """提交请假申请"""
    course_id: int
    type: LeaveType
    start_time: datetime
    end_time: datetime
    reason: str
    file_url: Optional[str] = None
    
    @validator('end_time')
    def validate_time(cls, v, values):
        if 'start_time' in values and v <= values['start_time']:
            raise ValueError('结束时间必须晚于开始时间')
        return v


class LeaveResponse(BaseModel):
    """请假申请响应"""
    id: int
    student_id: int
    student_name: Optional[str] = None # 补充字段
    course_id: int
    course_name: Optional[str] = None # 补充字段
    teacher_id: int
    teacher_name: Optional[str] = None # 补充字段
    type: str
    start_time: datetime
    end_time: datetime
    reason: str
    file_url: Optional[str]
    status: str
    opinion: Optional[str]
    approve_time: Optional[datetime]
    create_time: datetime

    class Config:
        from_attributes = True


class LeaveApprove(BaseModel):
    """审批请假"""
    leave_id: int
    result: str  # approved/rejected
    opinion: Optional[str] = None


class LeaveRecall(BaseModel):
    """撤回请假"""
    leave_id: int
