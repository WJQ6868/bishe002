import asyncio
from sqlalchemy import text
from app.database import AsyncSessionLocal

async def clean_data():
    async with AsyncSessionLocal() as session:
        print("Cleaning up demo data...")
        
        # 1. 清理 students 表（仅保留非演示数据，或全清重新生成）
        # 之前的逻辑生成了 S00001~S03500，这里删除所有 S 开头的演示账号
        await session.execute(text("DELETE FROM students WHERE id LIKE 'S%'"))
        await session.execute(text("DELETE FROM students WHERE id LIKE '2021%'")) # 图片中的旧数据
        
        # 2. 清理 teachers 表（保留 100001，删除 教师1~教师85）
        await session.execute(text("DELETE FROM teachers WHERE name LIKE '教师%'"))
        
        # 3. 清理 sys_users 表（删除非核心账号）
        # 保留 admin(800001), teacher(100001), student(20230001-20230004)
        keep_users = ['800001', '100001', '20230001', '20230002', '20230003', '20230004', 'admin', 'teacher', 'student']
        placeholders = ','.join([f"'{u}'" for u in keep_users])
        await session.execute(text(f"DELETE FROM sys_users WHERE username NOT IN ({placeholders})"))
        
        # 4. 清理 user_profiles (级联清理，或手动清理孤儿数据)
        await session.execute(text("DELETE FROM user_profiles WHERE user_id NOT IN (SELECT id FROM sys_users)"))
        
        # 5. 清理 courses 表（清理 课程1~课程120）
        await session.execute(text("DELETE FROM courses WHERE name LIKE '课程%'"))
        
        # 6. 清理 classrooms 表（清理 教室-101~教室-140）
        await session.execute(text("DELETE FROM classrooms WHERE name LIKE '教室-%'"))

        await session.commit()
        print("Cleanup complete.")

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(clean_data())
