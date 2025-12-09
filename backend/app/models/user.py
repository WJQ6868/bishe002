from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from ..database import Base

class User(Base):
    __tablename__ = "sys_users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password = Column(String(100), nullable=False)  # Plain text password
    role = Column(String(20), nullable=False) # admin, teacher, student
    is_active = Column(Boolean, default=True)


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("sys_users.id"), unique=True, nullable=False)
    name = Column(String(50), nullable=True)
    dept = Column(String(50), nullable=True)
    grade = Column(String(20), nullable=True)
    entry_time = Column(DateTime, nullable=True)
    create_time = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")
