from sqlalchemy import Column, String
from ..database import Base

class Admin(Base):
    __tablename__ = "admins"

    id = Column(String(20), primary_key=True) # 工号/账号
    name = Column(String(50), nullable=False)
    # password = Column(String(100), nullable=False)  # 明文密码 - 数据库真实表中无此字段
    dept = Column(String(50), nullable=True)
    phone = Column(String(20), nullable=True)
