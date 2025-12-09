from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, UniqueConstraint, Text, DateTime, func
from sqlalchemy.orm import relationship
from ..database import Base

class Classroom(Base):
    __tablename__ = "classrooms"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False, unique=True)
    capacity = Column(Integer, nullable=False)
    is_multimedia = Column(Boolean, default=False)

    schedules = relationship("Schedule", back_populates="classroom")
    resource = relationship(
        "ClassroomResource",
        back_populates="classroom",
        cascade="all, delete-orphan",
        uselist=False,
    )

class Schedule(Base):
    __tablename__ = "schedules"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    classroom_id = Column(Integer, ForeignKey("classrooms.id"), nullable=False)
    teacher_id = Column(String(20), ForeignKey("teachers.id"), nullable=False)
    
    day = Column(Integer, nullable=False) # 0-4 for Mon-Fri
    period = Column(Integer, nullable=False) # 0-5 for 1-6 periods
    
    # Relationships
    course = relationship("Course")
    classroom = relationship("Classroom", back_populates="schedules")
    teacher = relationship("Teacher")

    # Constraints to prevent conflicts (DB level)
    __table_args__ = (
        UniqueConstraint('classroom_id', 'day', 'period', name='uq_classroom_time'),
        UniqueConstraint('teacher_id', 'day', 'period', name='uq_teacher_time'),
    )


class ClassroomResource(Base):
    __tablename__ = "classroom_resources"

    id = Column(Integer, primary_key=True, index=True)
    classroom_id = Column(Integer, ForeignKey("classrooms.id", ondelete="CASCADE"), unique=True, nullable=False)
    code = Column(String(50), unique=True, nullable=True)
    location = Column(String(100), nullable=True)
    devices = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="idle")
    remark = Column(String(255), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    classroom = relationship("Classroom", back_populates="resource")
