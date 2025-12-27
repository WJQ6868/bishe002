from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from ..database import Base


class Dept(Base):
    __tablename__ = "t_dept"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    parent_id = Column(Integer, ForeignKey("t_dept.id"), nullable=True)
    create_time = Column(DateTime, default=datetime.now)
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class ClassRoom(Base):
    __tablename__ = "t_class"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    grade_id = Column(Integer, nullable=False)
    head_teacher_id = Column(Integer, ForeignKey("t_teacher.id"), nullable=True)
    create_time = Column(DateTime, default=datetime.now)
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class TeacherUser(Base):
    __tablename__ = "t_teacher"

    id = Column(Integer, primary_key=True, index=True)
    teacher_no = Column(String(32), unique=True, nullable=False, index=True)
    name = Column(String(50), nullable=False)
    gender = Column(Integer, nullable=False)
    age = Column(Integer, nullable=True)
    mobile = Column(String(20), unique=True, nullable=True)
    email = Column(String(64), unique=True, nullable=True)
    dept_id = Column(Integer, ForeignKey("t_dept.id"), nullable=False)
    post_type = Column(Integer, nullable=False)  # 1教师/2行政/3教辅/4后勤
    subject = Column(String(50), nullable=True)
    title = Column(Integer, nullable=True)  # 1初级/2中级/3高级
    entry_time = Column(DateTime, nullable=True)
    leave_status = Column(Integer, nullable=False, default=1)  # 1在职/2离职
    teach_years = Column(Integer, nullable=True)
    role = Column(String(50), nullable=True)
    permissions = Column(String(500), nullable=True)  # JSON string
    status = Column(Integer, nullable=False, default=1)  # 1启用/2禁用
    last_login_time = Column(DateTime, nullable=True)
    last_login_ip = Column(String(64), nullable=True)
    create_time = Column(DateTime, default=datetime.now)
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    dept = relationship("Dept")


class StudentUser(Base):
    __tablename__ = "t_student"

    id = Column(Integer, primary_key=True, index=True)
    student_no = Column(String(32), unique=True, nullable=False, index=True)
    name = Column(String(50), nullable=False)
    gender = Column(Integer, nullable=False)
    age = Column(Integer, nullable=True)
    mobile = Column(String(20), nullable=True)
    parent_mobile = Column(String(20), nullable=False)
    grade_id = Column(Integer, nullable=False)
    class_id = Column(Integer, ForeignKey("t_class.id"), nullable=False)
    major = Column(String(50), nullable=True)
    enrollment_time = Column(DateTime, nullable=True)
    student_status = Column(Integer, nullable=False, default=1)  # 1正常/2休学/3转学/4退学/5毕业
    role = Column(String(50), nullable=True)
    permissions = Column(String(500), nullable=True)
    status = Column(Integer, nullable=False, default=1)  # 1启用/2禁用
    last_login_time = Column(DateTime, nullable=True)
    last_login_ip = Column(String(64), nullable=True)
    create_time = Column(DateTime, default=datetime.now)
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    classroom = relationship("ClassRoom", primaryjoin="ClassRoom.id==StudentUser.class_id", viewonly=True)
