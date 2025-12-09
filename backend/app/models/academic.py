from datetime import datetime
from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from ..database import Base


class AcademicMajor(Base):
    __tablename__ = "academic_majors"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), unique=True, nullable=False)
    create_time = Column(DateTime, default=datetime.utcnow)

    classes = relationship(
        "AcademicClass",
        back_populates="major",
        cascade="all, delete-orphan",
    )
    courses = relationship(
        "AcademicCourse",
        back_populates="major",
        cascade="all, delete-orphan",
    )


class AcademicClass(Base):
    __tablename__ = "academic_classes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    major_id = Column(Integer, ForeignKey("academic_majors.id"), nullable=False)
    name = Column(String(50), nullable=False)
    student_count = Column(Integer, nullable=False)
    create_time = Column(DateTime, default=datetime.utcnow)

    major = relationship("AcademicMajor", back_populates="classes")
    students = relationship(
        "AcademicStudent",
        back_populates="clazz",
        cascade="all, delete-orphan",
    )


class AcademicStudent(Base):
    __tablename__ = "academic_students"

    id = Column(Integer, primary_key=True, autoincrement=True)
    class_id = Column(Integer, ForeignKey("academic_classes.id"), nullable=False)
    student_code = Column(String(20), unique=True, nullable=False)
    name = Column(String(50), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    clazz = relationship("AcademicClass", back_populates="students")


class AcademicCourse(Base):
    __tablename__ = "academic_courses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    major_id = Column(Integer, ForeignKey("academic_majors.id"), nullable=False)
    name = Column(String(100), nullable=False)
    credit = Column(Float, nullable=False)
    class_hours = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    major = relationship("AcademicMajor", back_populates="courses")
    teachers = relationship(
        "AcademicCourseTeacher",
        back_populates="course",
        cascade="all, delete-orphan",
    )


class AcademicCourseTeacher(Base):
    __tablename__ = "academic_course_teachers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    course_id = Column(Integer, ForeignKey("academic_courses.id"), nullable=False)
    teacher_id = Column(String(20), ForeignKey("teachers.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    course = relationship("AcademicCourse", back_populates="teachers")
    teacher = relationship("Teacher")

    __table_args__ = (
        UniqueConstraint(
            "course_id",
            "teacher_id",
            name="uq_academic_course_teacher",
        ),
    )
