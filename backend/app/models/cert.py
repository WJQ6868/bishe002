from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from ..database import Base

class CertLink(Base):
    __tablename__ = "cert_links"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    category = Column(String, index=True, nullable=False)  # 计算机类, 英语类, etc.
    icon = Column(String, nullable=True)  # Icon name
    url = Column(String, nullable=False)
    description = Column(String, nullable=True)
    is_hot = Column(Boolean, default=False)
    is_official = Column(Boolean, default=True)
    click_count = Column(Integer, default=0)
    create_time = Column(DateTime, default=datetime.utcnow)

class UserCollection(Base):
    __tablename__ = "user_collections"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("sys_users.id"), nullable=False)
    link_id = Column(Integer, ForeignKey("cert_links.id"), nullable=False)
    collect_time = Column(DateTime, default=datetime.utcnow)

    # Relationships
    link = relationship("CertLink")
