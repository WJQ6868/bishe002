from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
from ..database import Base
import enum

class ExamType(str, enum.Enum):
    MIDTERM = "midterm"
    FINAL = "final"

class WarningLevel(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class Student(Base):
    __tablename__ = "students"

    id = Column(String(20), primary_key=True, index=True) # student_id
    name = Column(String(50))
    major = Column(String(50))
    grade = Column(String(20)) # e.g. "2023"
    
    grades = relationship("Grade", back_populates="student")
    behaviors = relationship("CourseSelection", back_populates="student")
    warnings = relationship("StudentWarning", back_populates="student")

class Grade(Base):
    __tablename__ = "grades"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(String(20), ForeignKey("students.id"))
    course_id = Column(Integer, ForeignKey("courses.id"))
    score = Column(Float)
    exam_type = Column(String(20)) # midterm, final. Using String for simplicity or Enum
    
    student = relationship("Student", back_populates="grades")
    course = relationship("Course")

class CourseSelection(Base):
    __tablename__ = "course_selections"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(String(20), ForeignKey("students.id"))
    course_id = Column(Integer, ForeignKey("courses.id"))
    absent_count = Column(Integer, default=0)
    submit_homework_rate = Column(Float, default=1.0)
    
    student = relationship("Student", back_populates="behaviors")

class StudentWarning(Base):
    __tablename__ = "student_warnings"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(String(20), ForeignKey("students.id"))
    warning_level = Column(String(20)) # high, medium, low
    warning_reason = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    student = relationship("Student", back_populates="warnings")
