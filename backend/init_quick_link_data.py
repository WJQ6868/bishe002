import asyncio
import sys
import os

sys.path.append(os.getcwd())

from app.database import engine, Base, AsyncSessionLocal
from app.models.quick_link import QuickLink
from app.models.user import User
from sqlalchemy.future import select

async def init_quick_link_data():
    print("Initializing quick links data...")
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    async with AsyncSessionLocal() as session:
        # Check if data exists
        result = await session.execute(select(QuickLink))
        if result.scalars().first():
            print("Quick links data already exists.")
            return

        # Sample data
        links = [
            QuickLink(
                name="校历安排",
                description="查看学期校历、放假安排",
                icon="Calendar",
                icon_bg="#e8f5e9",
                icon_color="#4caf50",
                route="/calendar",
                roles="all",
                sort_order=1
            ),
            QuickLink(
                name="请假申请",
                description="在线提交请假申请",
                icon="Clock",
                icon_bg="#fff3e0",
                icon_color="#ff9800",
                route="/student/leave-apply",
                roles="student",
                sort_order=2
            ),
            QuickLink(
                name="我的申请",
                description="查看申请进度",
                icon="List",
                icon_bg="#e3f2fd",
                icon_color="#2196f3",
                route="/service/my-applications",
                roles="all",
                sort_order=3
            ),
        ]
        
        session.add_all(links)
        await session.commit()
        print("Quick links data initialized successfully!")

if __name__ == "__main__":
    asyncio.run(init_quick_link_data())
