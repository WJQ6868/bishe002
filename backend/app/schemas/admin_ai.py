from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AiModelApiBase(BaseModel):
    name: str = Field(..., description="展示名称")
    provider: str = Field(..., description="dashscope_openai / ark_responses")
    provider_brand: Optional[str] = Field(None, description="OpenAI / DeepSeek / AzureOpenAI 等")
    model_name: str = Field(..., description="模型名/版本")
    endpoint: str = Field(..., description="接口地址或 base url")
    api_key: str = Field(..., description="API Key")
    api_header: Optional[str] = Field(None, description="额外 Header（JSON 串）")
    api_version: Optional[str] = Field(None, description="API 版本号（Azure/OpenAI）")
    timeout_seconds: int = Field(30, ge=1, le=600)
    quota_per_hour: int = Field(0, ge=0)
    temperature: Optional[float] = Field(None, ge=0, le=2)
    max_output_tokens: Optional[int] = Field(None, ge=32, le=32768)
    enabled: bool = True
    is_default: bool = False


class AiModelApiCreate(AiModelApiBase):
    pass


class AiModelApiUpdate(BaseModel):
    name: Optional[str] = None
    provider: Optional[str] = None
    provider_brand: Optional[str] = None
    model_name: Optional[str] = None
    endpoint: Optional[str] = None
    api_key: Optional[str] = None
    api_header: Optional[str] = None
    api_version: Optional[str] = None
    timeout_seconds: Optional[int] = Field(default=None, ge=1, le=600)
    quota_per_hour: Optional[int] = Field(default=None, ge=0)
    temperature: Optional[float] = Field(default=None, ge=0, le=2)
    max_output_tokens: Optional[int] = Field(default=None, ge=32, le=32768)
    enabled: Optional[bool] = None
    is_default: Optional[bool] = None


class AiModelApiOut(BaseModel):
    id: int
    name: str
    provider: str
    provider_brand: Optional[str] = None
    model_name: str
    endpoint: str
    api_header: Optional[str] = None
    api_version: Optional[str] = None
    timeout_seconds: int
    quota_per_hour: int
    temperature: Optional[float] = None
    max_output_tokens: Optional[int] = None
    enabled: bool
    is_default: bool
    created_at: datetime
    updated_at: datetime


class AiKnowledgeBaseCreate(BaseModel):
    name: str
    slug: Optional[str] = None
    description: Optional[str] = None
    feature: Optional[str] = None
    is_default: Optional[bool] = False


class AiKnowledgeBaseUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    feature: Optional[str] = None
    is_default: Optional[bool] = None


class AiKnowledgeBaseOut(BaseModel):
    id: int
    slug: str
    name: str
    description: Optional[str] = None
    owner_type: str
    owner_user_id: Optional[int] = None
    course_id: Optional[int] = None
    feature: Optional[str] = None
    is_default: bool = False
    document_count: int = 0
    chunk_count: int = 0
    created_at: datetime
    updated_at: Optional[datetime] = None


class AiModelApiTestRequest(BaseModel):
    api_id: Optional[int] = None
    provider: str
    model_name: str
    endpoint: str
    api_key: Optional[str] = None
    timeout_seconds: int = 30
    prompt: Optional[str] = None


class AiModelApiTestResponse(BaseModel):
    ok: bool
    message: str
    output: Optional[str] = None


class AiKbSubjectCreate(BaseModel):
    name: str
    stage: Optional[str] = None


class AiKbSubjectOut(BaseModel):
    id: int
    name: str
    stage: Optional[str] = None
    enabled: bool = True
    created_at: datetime


class AiKbDocumentOut(BaseModel):
    id: int
    subject_id: int
    knowledge_base_id: Optional[int] = None
    title: str
    original_filename: str
    url: str
    file_ext: str
    file_size: int
    enabled: bool = True
    created_at: datetime
    updated_at: Optional[datetime] = None
    chunk_count: Optional[int] = None


class AiModelKbUpdateRequest(BaseModel):
    kb_document_ids: List[int] = Field(default_factory=list)


class AiCustomModelKbDocOut(BaseModel):
    id: int
    title: str
    subject_id: int
    subject_name: Optional[str] = None


class AiCustomModelCreate(BaseModel):
    name: str
    remark: Optional[str] = None
    enabled: bool = True
    base_model_api_id: int
    primary_subject_id: Optional[int] = None
    kb_document_ids: List[int] = Field(default_factory=list)


class AiCustomModelUpdate(BaseModel):
    name: Optional[str] = None
    remark: Optional[str] = None
    enabled: Optional[bool] = None
    base_model_api_id: Optional[int] = None
    primary_subject_id: Optional[int] = None
    kb_document_ids: Optional[List[int]] = None


class AiCustomModelOut(BaseModel):
    id: int
    name: str
    remark: Optional[str] = None
    enabled: bool
    base_model_api_id: int
    base_model_name: Optional[str] = None
    primary_subject_id: Optional[int] = None
    primary_subject_name: Optional[str] = None
    kb_documents: List[AiCustomModelKbDocOut] = Field(default_factory=list)
    created_at: datetime
    updated_at: Optional[datetime] = None


class AiFeatureBindingOut(BaseModel):
    feature: str
    custom_model_ids: List[int] = Field(default_factory=list)


class AiFeatureBindingUpdate(BaseModel):
    custom_model_ids: List[int] = Field(default_factory=list)


class AiCustomerServiceSettingsOut(BaseModel):
    welcome_str: str = ""
    recommend_questions: List[str] = Field(default_factory=list)
    search_placeholder: str = ""
    system_prompt_template: Optional[str] = None


class AiCustomerServiceSettingsUpdate(BaseModel):
    welcome_str: Optional[str] = None
    recommend_questions: Optional[List[str]] = None
    search_placeholder: Optional[str] = None
    system_prompt_template: Optional[str] = None


class PublicAiModelOut(BaseModel):
    id: int
    name: str
    provider: str
    model_name: str
    is_default: bool
    subjects: List[str] = Field(default_factory=list)


class AiWorkflowAppOut(BaseModel):
    code: str
    type: str
    name: str
    status: str
    knowledge_base_id: Optional[int] = None
    model_api_id: Optional[int] = None
    owner_user_id: Optional[int] = None
    course_id: Optional[int] = None
    settings: Dict[str, Any] = Field(default_factory=dict)
    updated_at: Optional[datetime] = None


class AiWorkflowAppCreate(BaseModel):
    code: str
    type: str
    name: str
    status: Optional[str] = "enabled"
    knowledge_base_id: Optional[int] = None
    model_api_id: Optional[int] = None
    owner_user_id: Optional[int] = None
    course_id: Optional[int] = None
    settings: Optional[Dict[str, Any]] = None


class AiWorkflowAppUpdate(BaseModel):
    name: Optional[str] = None
    knowledge_base_id: Optional[int] = None
    model_api_id: Optional[int] = None
    status: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None


class StudentCourseAiSelectRequest(BaseModel):
    course_id: int
    model_api_id: Optional[int] = None


class StudentCourseAiSelectOut(BaseModel):
    course_id: int
    model_api_id: Optional[int] = None
