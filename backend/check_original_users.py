import asyncio
import sys
import os
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from app.database import DATABASE_URL
from app.models.user import User
from app.models.course import Teacher
from app.models.student import Student
from app.models.admin import Admin

async def check_users():
    engine = create_async_engine(DATABASE_URL, echo=False)
    AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with AsyncSessionLocal() as session:
        print("Checking for original users...")
        
        usernames = ["admin", "teacher", "student"]
        
        # Check Users table
        print("\n--- Users Table ---")
        for username in usernames:
            result = await session.execute(select(User).where(User.username == username))
            user = result.scalars().first()
            if user:
                print(f"User '{username}' found: ID={user.id}, Role={user.role}")
            else:
                print(f"User '{username}' NOT found.")

        # Check Role Tables
        print("\n--- Role Tables ---")
        
        # Admin
        result = await session.execute(select(Admin).where(Admin.id == "admin")) # Assuming ID matches username for these special ones, or we need to find out their IDs
        admin = result.scalars().first()
        if admin:
             print(f"Admin 'admin' found in Admins table.")
        else:
             # Try to find by name or other means if ID is different, but for now check ID
             print(f"Admin 'admin' NOT found in Admins table (checking ID='admin').")

        # Teacher
        result = await session.execute(select(Teacher).where(Teacher.id == "teacher"))
        teacher = result.scalars().first()
        if teacher:
             print(f"Teacher 'teacher' found in Teachers table.")
        else:
             print(f"Teacher 'teacher' NOT found in Teachers table (checking ID='teacher').")

        # Student
        result = await session.execute(select(Student).where(Student.id == "student"))
        student = result.scalars().first()
        if student:
             print(f"Student 'student' found in Students table.")
        else:
             print(f"Student 'student' NOT found in Students table (checking ID='student').")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(check_users())
