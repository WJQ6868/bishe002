from sqlalchemy import Column, DateTime, Integer, String, Text
from datetime import datetime

from ..database import Base


class FrontendLog(Base):
    __tablename__ = "frontend_logs"

    id = Column(Integer, primary_key=True, index=True)
    level = Column(String(32), nullable=False)
    message = Column(Text, nullable=False)
    data = Column(Text, nullable=True)
    client_time = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
