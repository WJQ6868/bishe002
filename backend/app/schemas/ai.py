from pydantic import BaseModel, Field
from typing import Optional

class QARequest(BaseModel):
    user_id: str = Field(..., description="用户ID")
    question: str = Field(..., description="用户问题")
    history_flag: bool = Field(True, description="是否携带历史上下文")
    model: Optional[str] = Field(None, description="模型键名")
    workflow: Optional[str] = Field(None, description="可选：customer_service 工作流 code")
    course_id: Optional[int] = Field(None, description="课程ID（用于学生专属课程AI）")

class QAStreamResponse(BaseModel):
    content: str
