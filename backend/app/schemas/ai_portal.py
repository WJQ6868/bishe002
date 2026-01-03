from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class PublicAiModelApiOut(BaseModel):
    id: int
    name: str
    provider: str
    model_name: str
    endpoint: str
    enabled: bool
    is_default: bool
    updated_at: Optional[datetime] = None


class TeacherCourseOut(BaseModel):
    id: int
    name: str


class TeacherKbDocumentOut(BaseModel):
    id: int
    course_id: Optional[int] = None
    subject: str
    title: str
    original_filename: str
    url: str
    file_ext: str
    file_size: int
    created_at: datetime
    updated_at: Optional[datetime] = None


class TeacherKbUpdateRequest(BaseModel):
    title: Optional[str] = None
    subject: Optional[str] = None
    course_id: Optional[int] = None


class StudentCourseAiItemOut(BaseModel):
    course_id: int
    course_name: str
    teacher_id: Optional[str] = None
    teacher_name: str
    teacher_kb_updated_at: Optional[datetime] = None

    selected_model_api_id: Optional[int] = None
    favorite: bool = False


class StudentCourseAiSelectRequest(BaseModel):
    course_id: int = Field(..., ge=1)
    model_api_id: Optional[int] = Field(None, description="为空表示清除该课程专属模型")


class StudentCourseAiFavoriteRequest(BaseModel):
    course_id: int = Field(..., ge=1)
    favorite: bool = True


class LessonPlanTaskCreate(BaseModel):
    title: str = Field(..., description="教案标题", max_length=200)
    outline: Optional[str] = Field(None, description="课件大纲/思路")
    course_id: Optional[int] = Field(None, description="关联课程，可选")


class LessonPlanTaskResultUpdate(BaseModel):
    status: Optional[str] = Field(None, description="pending/streaming/completed/failed")
    result: Optional[str] = Field(None, description="生成的教案内容")
    error_message: Optional[str] = None


class LessonPlanTaskOut(BaseModel):
    id: int
    title: str
    outline: Optional[str] = None
    course_id: Optional[int] = None
    status: str
    result: Optional[str] = None
    error_message: Optional[str] = None
    knowledge_base_id: Optional[int] = None
    model_api_id: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
