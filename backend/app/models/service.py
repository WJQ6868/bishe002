from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
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
