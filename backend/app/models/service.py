from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from ..database import Base
from datetime import datetime
import json

class ServiceItem(Base):
    __tablename__ = "service_item"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    category = Column(String(50), nullable=False)  # student_management/course_management/score_management/certificate/other
    icon = Column(String(100))
    processing_time = Column(String(50), nullable=False)
    status = Column(String(20), default='available')  # available/paused
    guide = Column(Text, nullable=False)  # Rich text
    apply_conditions = Column(Text, nullable=False)  # Rich text
    required_materials = Column(Text, nullable=False)  # JSON string
    process = Column(Text, nullable=False)  # JSON string
    apply_fields = Column(Text, nullable=False)  # JSON string
    create_time = Column(DateTime, default=datetime.now)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "icon": self.icon,
            "processing_time": self.processing_time,
            "status": self.status,
            "guide": self.guide,
            "apply_conditions": self.apply_conditions,
            "required_materials": json.loads(self.required_materials) if self.required_materials else [],
            "process": json.loads(self.process) if self.process else [],
            "apply_fields": json.loads(self.apply_fields) if self.apply_fields else [],
            "create_time": self.create_time
        }

class ServiceApply(Base):
    __tablename__ = "service_apply"

    id = Column(Integer, primary_key=True, index=True)
    item_id = Column(Integer, ForeignKey("service_item.id"), nullable=False)
    applicant_id = Column(Integer, ForeignKey("sys_users.id"), nullable=False)
    applicant_role = Column(String(20), nullable=False)
    form_data = Column(Text, nullable=False)  # JSON string
    materials = Column(Text)  # JSON string
    status = Column(String(20), default='pending')  # pending/approved/rejected/processing/completed
    progress_nodes = Column(Text, nullable=False)  # JSON string
    submit_time = Column(DateTime, default=datetime.now)
    approve_time = Column(DateTime)
    approver_id = Column(Integer, ForeignKey("sys_users.id"))
    opinion = Column(Text)

    def to_dict(self):
        return {
            "id": self.id,
            "item_id": self.item_id,
            "applicant_id": self.applicant_id,
            "applicant_role": self.applicant_role,
            "form_data": json.loads(self.form_data) if self.form_data else {},
            "materials": json.loads(self.materials) if self.materials else [],
            "status": self.status,
            "progress_nodes": json.loads(self.progress_nodes) if self.progress_nodes else [],
            "submit_time": self.submit_time,
            "approve_time": self.approve_time,
            "approver_id": self.approver_id,
            "opinion": self.opinion
        }


class ServiceApplyConfig(Base):
    __tablename__ = "service_apply_config"

    id = Column(Integer, primary_key=True, index=True)
    service_item_id = Column(Integer, ForeignKey("service_item.id"), nullable=True)
    role_scope = Column(String(20), default="all")  # student/teacher/all
    display_order = Column(Integer, default=0)
    entry_positions = Column(Text, default="[]")  # JSON list: service_hall/dashboard/personal_center
    unread_badge = Column(Boolean, default=False)
    duration_rules = Column(Text, default="{}")  # submit_expire_hours/review_timeout_hours/timeout_strategy/timeout_channels
    approval_flow = Column(Text, default="[]")  # list of nodes
    notification_rules = Column(Text, default="{}")  # event -> channels/templates
    status_meta = Column(Text, default="{}")  # status -> {label,color}
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def to_dict(self):
        return {
            "id": self.id,
            "service_item_id": self.service_item_id,
            "role_scope": self.role_scope,
            "display_order": self.display_order,
            "entry_positions": json.loads(self.entry_positions) if self.entry_positions else [],
            "unread_badge": bool(self.unread_badge),
            "duration_rules": json.loads(self.duration_rules) if self.duration_rules else {},
            "approval_flow": json.loads(self.approval_flow) if self.approval_flow else [],
            "notification_rules": json.loads(self.notification_rules) if self.notification_rules else {},
            "status_meta": json.loads(self.status_meta) if self.status_meta else {},
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class ServiceUpload(Base):
    __tablename__ = "service_upload"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("sys_users.id"), nullable=False)
    original_name = Column(String(255), nullable=False)
    stored_path = Column(String(500), nullable=False)
    mime_type = Column(String(100))
    size = Column(Integer)
    created_at = Column(DateTime, default=datetime.now)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "original_name": self.original_name,
            "stored_path": self.stored_path,
            "mime_type": self.mime_type,
            "size": self.size,
            "created_at": self.created_at,
        }
