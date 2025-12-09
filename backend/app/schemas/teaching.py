"""
教师教学管理 - Pydantic 模型
"""
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List
from enum import Enum


# --- 枚举定义 (需与 models 保持一致) ---

class AttendanceStatus(str, Enum):
    PRESENT = "已签到"
    LATE = "迟到"
    ABSENT = "未到"
    LEAVE = "请假"


class HomeworkType(str, Enum):
    SUBJECTIVE = "主观题"
    OBJECTIVE = "客观题"
    FILE = "文件提交"


class HomeworkStatus(str, Enum):
    PENDING = "待提交"
    SUBMITTED = "已提交"
    GRADED = "已批改"
    RETURNED = "需重交"
    RESUBMITTED = "待复审"


class AdjustStatus(str, Enum):
    PENDING = "待审核"
    APPROVED = "已通过"
    REJECTED = "已拒绝"


class WorkType(str, Enum):
    CLASS = "上课"
    MEETING = "开会"
    DUTY = "值班"
    OTHER = "其他"


# --- 模型定义 ---

# 点名
class AttendanceCreate(BaseModel):
    course_id: int
    duration: int = 5  # 有效期 (分钟)


class AttendanceSign(BaseModel):
    code: str  # 签到码
    student_id: int
    location: Optional[str] = None


class AttendanceUpdate(BaseModel):
    id: int
    status: AttendanceStatus
    remark: Optional[str] = None


class AttendanceResponse(BaseModel):
    id: int
    course_id: int
    student_id: int
    student_name: Optional[str] = None
    status: str
    sign_time: Optional[datetime]
    remark: Optional[str]
    create_time: datetime

    class Config:
        from_attributes = True


# 作业
class HomeworkCreate(BaseModel):
    title: str
    course_id: int
    content: str
    deadline: datetime
    type: HomeworkType
    score: int = 100
    file_url: Optional[str] = None


class HomeworkResponse(BaseModel):
    id: int
    title: str
    course_id: int
    course_name: Optional[str] = None
    teacher_id: int
    content: str
    deadline: datetime
    type: str
    score: int
    file_url: Optional[str]
    create_time: datetime

    class Config:
        from_attributes = True


class HomeworkSubmitCreate(BaseModel):
    homework_id: int
    content: Optional[str] = None
    file_url: Optional[str] = None


class HomeworkSubmitResponse(BaseModel):
    id: int
    homework_id: int
    student_id: int
    student_name: Optional[str] = None
    content: Optional[str]
    file_url: Optional[str]
    submit_time: datetime
    status: str
    score: Optional[float]
    comment: Optional[str]

    class Config:
        from_attributes = True


class HomeworkGrade(BaseModel):
    submit_id: int
    score: float
    comment: Optional[str] = None
    status: HomeworkStatus = HomeworkStatus.GRADED


# 调课
class ClassAdjustCreate(BaseModel):
    course_id: int
    old_time: datetime
    new_time: datetime
    old_classroom: Optional[str] = None
    new_classroom: Optional[str] = None
    reason: str
    file_url: Optional[str] = None


class ClassAdjustResponse(BaseModel):
    id: int
    teacher_id: int
    course_id: int
    course_name: Optional[str] = None
    old_time: datetime
    new_time: datetime
    reason: str
    status: str
    create_time: datetime

    class Config:
        from_attributes = True


class ClassAdjustAdminItem(BaseModel):
    id: int
    teacher_id: int
    teacher_name: Optional[str] = None
    course_id: int
    course_name: Optional[str] = None
    old_time: datetime
    new_time: datetime
    old_classroom: Optional[str] = None
    new_classroom: Optional[str] = None
    reason: str
    status: str
    create_time: datetime

    class Config:
        from_attributes = True


# 工作安排
class WorkScheduleCreate(BaseModel):
    time: datetime
    content: str
    type: WorkType
    remark: Optional[str] = None


class WorkScheduleResponse(BaseModel):
    id: int
    teacher_id: int
    time: datetime
    content: str
    type: str
    remark: Optional[str]

    class Config:
        from_attributes = True
