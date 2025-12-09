from sqlalchemy import Column, Integer, String, Text, DateTime
from ..database import Base
from datetime import datetime

class CalendarEvent(Base):
    __tablename__ = "calendar_event"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(100), nullable=False)
    type = Column(String(50), nullable=False)  # 节假日/考试/活动/其他
    start_date = Column(String(20), nullable=False)  # YYYY-MM-DD 字符串存储适配 SQLite
    end_date = Column(String(20), nullable=False)    # YYYY-MM-DD
    location = Column(String(100))
    related_classes = Column(String(255))  # 逗号分隔的班级ID或名称
    description = Column(Text)
    create_time = Column(DateTime, default=datetime.now)
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now)
