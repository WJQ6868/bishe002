from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from ..database import Base

class CourseType(str, enum.Enum):
    REQUIRED = "必修"
    ELECTIVE = "选修"

class Teacher(Base):
    __tablename__ = "teachers"

    id = Column(String(20), primary_key=True, index=True)  # 教师工号
    name = Column(String(50), nullable=False)
    # password = Column(String(100), nullable=False)  # 明文密码 - 数据库真实表中无此字段
    # dept = Column(String(50), nullable=True)  # 所属部门 - 数据库真实表中无此字段
    # phone = Column(String(20), nullable=True)  # 联系电话 - 数据库真实表中无此字段

    courses = relationship("Course", back_populates="teacher")

class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    credit = Column(Integer, nullable=False)
    teacher_id = Column(String(20), ForeignKey("teachers.id"), nullable=False)  # 修改为 String 以匹配教师工号
    capacity = Column(Integer, nullable=False)
    course_type = Column(String(20), nullable=False)
    create_time = Column(DateTime, default=datetime.now)

    teacher = relationship("Teacher", back_populates="courses")
