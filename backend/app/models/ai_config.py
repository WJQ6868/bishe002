from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from ..database import Base


class AiModelApi(Base):
    __tablename__ = "ai_model_apis"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String(100), nullable=False)  # 展示名称
    provider = Column(String(50), nullable=False)  # dashscope_openai / ark_responses
    model_name = Column(String(100), nullable=False)  # 具体模型名/版本

    endpoint = Column(String(300), nullable=False)  # 完整接口地址或 base url
    api_key = Column(String(300), nullable=False)
    api_header = Column(Text, nullable=True)
    api_version = Column(String(50), nullable=True)
    provider_brand = Column(String(50), nullable=True)  # OpenAI / DeepSeek / AzureOpenAI / ...

    timeout_seconds = Column(Integer, nullable=False, default=30)
    quota_per_hour = Column(Integer, nullable=False, default=0)  # 0 表示不限制（仅配置位）
    temperature = Column(Float, nullable=True)
    max_output_tokens = Column(Integer, nullable=True)

    enabled = Column(Boolean, nullable=False, default=True)
    is_default = Column(Boolean, nullable=False, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    kb_links = relationship("AiModelKnowledgeBaseLink", back_populates="model", cascade="all, delete-orphan")
    workflow_apps = relationship("AiWorkflowApp", back_populates="model")
    lesson_plan_tasks = relationship("AiLessonPlanTask", back_populates="model")


class AiKnowledgeBase(Base):
    __tablename__ = "ai_knowledge_bases"
    __table_args__ = (UniqueConstraint("slug", name="uq_ai_kb_slug"),)

    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String(64), nullable=False, unique=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    owner_type = Column(String(30), nullable=False, default="system")  # system / teacher / course
    owner_user_id = Column(Integer, nullable=True)
    course_id = Column(Integer, nullable=True, index=True)
    feature = Column(String(50), nullable=True)
    is_default = Column(Boolean, nullable=False, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    documents = relationship("AiKnowledgeBaseDocument", back_populates="knowledge_base", cascade="all, delete-orphan")
    chunks = relationship("AiKnowledgeBaseChunk", back_populates="knowledge_base", cascade="all, delete-orphan")
    apps = relationship("AiWorkflowApp", back_populates="knowledge_base")
    lesson_plan_tasks = relationship("AiLessonPlanTask", back_populates="knowledge_base")


class AiKnowledgeBaseSubject(Base):
    __tablename__ = "ai_kb_subjects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)

    # 学段（可选）：如 小学/初中/高中/大学
    stage = Column(String(50), nullable=True)

    enabled = Column(Boolean, nullable=False, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    documents = relationship("AiKnowledgeBaseDocument", back_populates="subject", cascade="all, delete-orphan")


class AiKnowledgeBaseDocument(Base):
    __tablename__ = "ai_kb_documents"

    id = Column(Integer, primary_key=True, index=True)
    subject_id = Column(Integer, ForeignKey("ai_kb_subjects.id"), nullable=True, index=True)
    knowledge_base_id = Column(Integer, ForeignKey("ai_knowledge_bases.id"), nullable=True, index=True)

    title = Column(String(200), nullable=False)
    original_filename = Column(String(260), nullable=False)
    stored_filename = Column(String(260), nullable=False)
    url = Column(String(300), nullable=False)  # /static/... 直接可下载/预览
    file_ext = Column(String(20), nullable=False)
    file_size = Column(Integer, nullable=False, default=0)

    enabled = Column(Boolean, nullable=False, default=True)

    uploaded_by_admin = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    subject = relationship("AiKnowledgeBaseSubject", back_populates="documents")
    model_links = relationship("AiModelKnowledgeBaseLink", back_populates="document", cascade="all, delete-orphan")
    knowledge_base = relationship("AiKnowledgeBase", back_populates="documents")
    chunks = relationship("AiKnowledgeBaseChunk", back_populates="document", cascade="all, delete-orphan")


class AiKnowledgeBaseChunk(Base):
    __tablename__ = "ai_kb_chunks"

    id = Column(Integer, primary_key=True, index=True)
    knowledge_base_id = Column(Integer, ForeignKey("ai_knowledge_bases.id"), nullable=False, index=True)
    document_id = Column(Integer, ForeignKey("ai_kb_documents.id"), nullable=True, index=True)
    seq = Column(Integer, nullable=False, default=0)
    content = Column(Text, nullable=False)
    tokens = Column(Text, nullable=True)
    document_title = Column(String(200), nullable=True)
    document_url = Column(String(300), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    knowledge_base = relationship("AiKnowledgeBase", back_populates="chunks")
    document = relationship("AiKnowledgeBaseDocument", back_populates="chunks")


class AiModelKnowledgeBaseLink(Base):
    __tablename__ = "ai_model_kb_links"
    __table_args__ = (UniqueConstraint("model_api_id", "kb_document_id", name="uq_ai_model_kb"),)

    id = Column(Integer, primary_key=True, index=True)
    model_api_id = Column(Integer, ForeignKey("ai_model_apis.id"), nullable=False, index=True)
    kb_document_id = Column(Integer, ForeignKey("ai_kb_documents.id"), nullable=False, index=True)

    # 越小优先级越高（用于检索/拼接上下文时的排序）
    priority = Column(Integer, nullable=False, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)

    model = relationship("AiModelApi", back_populates="kb_links")
    document = relationship("AiKnowledgeBaseDocument", back_populates="model_links")


class TeacherKnowledgeBaseDocument(Base):
    __tablename__ = "teacher_kb_documents"

    id = Column(Integer, primary_key=True, index=True)
    owner_user_id = Column(Integer, nullable=False, index=True)  # User.id

    # 绑定到课程（用于“专属课程AI”按课程优先检索教师知识库）。
    # 为空表示通用教师私有知识库（仅用于教师端）。
    course_id = Column(Integer, nullable=True, index=True)

    subject = Column(String(100), nullable=False, default="")

    title = Column(String(200), nullable=False)
    original_filename = Column(String(260), nullable=False)
    stored_filename = Column(String(260), nullable=False)
    url = Column(String(300), nullable=False)
    file_ext = Column(String(20), nullable=False)
    file_size = Column(Integer, nullable=False, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class StudentCourseAiFavorite(Base):
    __tablename__ = "student_course_ai_favorites"
    __table_args__ = (UniqueConstraint("student_user_id", "course_id", name="uq_student_course_ai_fav"),)

    id = Column(Integer, primary_key=True, index=True)
    student_user_id = Column(Integer, nullable=False, index=True)  # User.id
    course_id = Column(Integer, nullable=False, index=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class StudentCourseAiSelection(Base):
    __tablename__ = "student_course_ai_selections"
    __table_args__ = (UniqueConstraint("student_user_id", "course_id", name="uq_student_course_ai"),)

    id = Column(Integer, primary_key=True, index=True)
    student_user_id = Column(Integer, nullable=False, index=True)  # User.id
    course_id = Column(Integer, nullable=False, index=True)

    # 兼容：旧逻辑使用 model_api_id
    model_api_id = Column(Integer, ForeignKey("ai_model_apis.id"), nullable=True)
    # 新逻辑：课程助手可绑定“定制模型”
    custom_model_id = Column(Integer, ForeignKey("ai_custom_models.id"), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


ALLOWED_KB_EXTS = {".txt", ".pdf", ".doc", ".docx", ".md", ".xlsx", ".xls", ".csv"}


class AiCustomModel(Base):
    """定制模型：= 1 个大模型底座 + N 个基础知识库文档（可排序）。"""

    __tablename__ = "ai_custom_models"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String(200), nullable=False)
    remark = Column(Text, nullable=True)

    base_model_api_id = Column(Integer, ForeignKey("ai_model_apis.id"), nullable=False, index=True)

    # 课程助手分组展示用（可选）
    primary_subject_id = Column(Integer, ForeignKey("ai_kb_subjects.id"), nullable=True, index=True)

    enabled = Column(Boolean, nullable=False, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    base_model = relationship("AiModelApi")
    primary_subject = relationship("AiKnowledgeBaseSubject")
    kb_links = relationship("AiCustomModelKnowledgeBaseLink", back_populates="custom_model", cascade="all, delete-orphan")


class AiCustomModelKnowledgeBaseLink(Base):
    __tablename__ = "ai_custom_model_kb_links"
    __table_args__ = (UniqueConstraint("custom_model_id", "kb_document_id", name="uq_ai_custom_model_kb"),)

    id = Column(Integer, primary_key=True, index=True)
    custom_model_id = Column(Integer, ForeignKey("ai_custom_models.id"), nullable=False, index=True)
    kb_document_id = Column(Integer, ForeignKey("ai_kb_documents.id"), nullable=False, index=True)

    priority = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    custom_model = relationship("AiCustomModel", back_populates="kb_links")
    document = relationship("AiKnowledgeBaseDocument")


class AiFeatureCustomModelBinding(Base):
    """AI 设置：将定制模型绑定到具体业务功能。"""

    __tablename__ = "ai_feature_custom_models"
    __table_args__ = (UniqueConstraint("feature", "custom_model_id", name="uq_ai_feature_custom_model"),)

    id = Column(Integer, primary_key=True, index=True)
    feature = Column(String(50), nullable=False, index=True)  # customer_service / lesson_plan / course_assistant
    custom_model_id = Column(Integer, ForeignKey("ai_custom_models.id"), nullable=False, index=True)
    sort_order = Column(Integer, nullable=False, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)

    custom_model = relationship("AiCustomModel")


class AiFeatureSetting(Base):
    """AI 设置：按业务功能保存可配置项（JSON）。

    目前用于 customer_service：welcome_str / recommend_questions / search_placeholder / system_prompt_template。
    """

    __tablename__ = "ai_feature_settings"
    __table_args__ = (UniqueConstraint("feature", name="uq_ai_feature_settings"),)

    id = Column(Integer, primary_key=True, index=True)
    feature = Column(String(50), nullable=False, index=True)
    settings_json = Column(Text, nullable=False, default="{}")

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AiWorkflowApp(Base):
    __tablename__ = "ai_workflow_apps"
    __table_args__ = (UniqueConstraint("code", name="uq_ai_workflow_app_code"),)

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(80), nullable=False, unique=True, index=True)
    type = Column(String(40), nullable=False)  # customer_service / course_assistant / lesson_plan
    name = Column(String(200), nullable=False)

    knowledge_base_id = Column(Integer, ForeignKey("ai_knowledge_bases.id"), nullable=True, index=True)
    model_api_id = Column(Integer, ForeignKey("ai_model_apis.id"), nullable=True, index=True)

    owner_user_id = Column(Integer, nullable=True, index=True)
    course_id = Column(Integer, nullable=True, index=True)
    settings_json = Column(Text, nullable=False, default="{}")
    status = Column(String(30), nullable=False, default="enabled")

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    knowledge_base = relationship("AiKnowledgeBase", back_populates="apps")
    model = relationship("AiModelApi", back_populates="workflow_apps")


class AiLessonPlanTask(Base):
    __tablename__ = "ai_lesson_plan_tasks"

    id = Column(Integer, primary_key=True, index=True)
    teacher_user_id = Column(Integer, nullable=False, index=True)
    course_id = Column(Integer, nullable=True, index=True)
    title = Column(String(200), nullable=False)
    outline = Column(Text, nullable=True)
    status = Column(String(30), nullable=False, default="pending")  # pending / streaming / completed / failed
    result = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)

    knowledge_base_id = Column(Integer, ForeignKey("ai_knowledge_bases.id"), nullable=True, index=True)
    model_api_id = Column(Integer, ForeignKey("ai_model_apis.id"), nullable=True, index=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    knowledge_base = relationship("AiKnowledgeBase", back_populates="lesson_plan_tasks")
    model = relationship("AiModelApi", back_populates="lesson_plan_tasks")


class AiUsageLog(Base):
    __tablename__ = "ai_usage_logs"

    id = Column(Integer, primary_key=True, index=True)
    feature = Column(String(50), nullable=False, index=True)  # customer_service / course_assistant / lesson_plan
    user_id = Column(Integer, nullable=True, index=True)
    user_role = Column(String(20), nullable=False, default="unknown", index=True)  # student / teacher / admin / unknown
    result = Column(String(20), nullable=False, default="success")  # success / failed
    message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
