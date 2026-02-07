from pydantic import BaseModel, Field
from typing import Optional

class QARequest(BaseModel):
    user_id: str = Field(..., description="用户ID")
    question: str = Field(..., description="用户问题")
    history_flag: bool = Field(True, description="是否携带历史上下文")
    # AI 助手：用于管理端模型/工作流的选择
    model: Optional[str] = Field(None, description="模型 ID (db:<id>) 或空")
    course_id: Optional[int] = Field(None, description="课程ID，用于选择课程知识库")
    workflow: Optional[str] = Field(None, description="工作流编码")

class QAStreamResponse(BaseModel):
    content: str
