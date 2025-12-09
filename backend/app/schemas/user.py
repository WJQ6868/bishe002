from pydantic import BaseModel
from datetime import datetime


class UserOut(BaseModel):
    id: int
    account: str
    name: str | None
    role: str
    dept: str | None
    grade: str | None
    entryTime: str | None
    status: bool
    createTime: str | None

    class Config:
        from_attributes = True


class UserQuery(BaseModel):
    keyword: str | None = None
    role: str | None = None


class UserCreate(BaseModel):
    """创建用户的请求模型"""
    account: str
    name: str
    password: str = "123456"  # 默认密码
    role: str  # student, teacher, admin
    dept: str | None = None
    grade: str | None = None  # 学生年级
    entry_time: str | None = None  # 教师入职时间


class UserUpdate(BaseModel):
    """更新用户信息的请求模型"""
    name: str | None = None
    dept: str | None = None
    grade: str | None = None
    entry_time: str | None = None
    status: bool | None = None
