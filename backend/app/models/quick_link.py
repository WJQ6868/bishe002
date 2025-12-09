from sqlalchemy import Column, Integer, String, Boolean
from ..database import Base

class QuickLink(Base):
    __tablename__ = "quick_links"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)  # 名称
    description = Column(String, nullable=True)  # 描述
    icon = Column(String, nullable=True)  # 图标名称
    icon_bg = Column(String, default="#e3f2fd")  # 图标背景色
    icon_color = Column(String, default="#2196f3")  # 图标颜色
    route = Column(String, nullable=False)  # 跳转路由
    roles = Column(String, default="all")  # 可见角色，逗号分隔，如 "student,teacher" 或 "all"
    sort_order = Column(Integer, default=0)  # 排序
    is_active = Column(Boolean, default=True)  # 是否启用
