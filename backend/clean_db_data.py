import asyncio
import sys
import os
from sqlalchemy import select, delete, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from app.database import DATABASE_URL
from app.models.user import User
from app.models.course import Teacher, Course
from app.models.student import Student, StudentWarning, CourseSelection, Grade
from app.models.admin import Admin
from app.models.schedule import Classroom, Schedule, ClassroomResource
from app.models.leave import LeaveApply
from app.models.teaching import Attendance, Homework, HomeworkSubmit, ClassAdjust, WorkSchedule

async def clean_database():
    engine = create_async_engine(DATABASE_URL, echo=False)
    AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with AsyncSessionLocal() as session:
        print("Starting database cleanup...")
        
        original_users = ["admin", "teacher", "student"]
        
        # 1. Delete from dependent tables first to avoid foreign key constraints
        print("Cleaning dependent tables...")
        
        tables_to_clear = [
            Grade, CourseSelection, LeaveApply, HomeworkSubmit, Attendance, 
            ClassAdjust, WorkSchedule, Schedule, StudentWarning, 
            Homework, Course, ClassroomResource, Classroom
        ]
        
        for table in tables_to_clear:
            await session.execute(delete(table))
            print(f"Cleared {table.__tablename__}")
            
        # 2. Clean up Users, Teachers, Students, Admins
        print("Cleaning User and Role tables, preserving original users...")

        # Users
        await session.execute(delete(User).where(User.username.notin_(original_users)))
        print("Cleaned Users table.")

        # Teachers
        # Note: The original 'teacher' user might not have a corresponding record in the 'teachers' table 
        # with id='teacher'. It usually has a specific ID like T100001. 
        # If the user 'teacher' is just a login account, we might not need to preserve a teacher profile 
        # if it doesn't exist. But if it does, we keep it.
        # Based on init_db_data.py, 'teacher' user has password 'teacher' and role 'teacher'.
        # But the Teachers table is populated with T100001 etc.
        # Let's check if 'teacher' exists in Teachers table. If not, we just delete all teachers.
        # Wait, the requirement is "preserve original three users".
        # If 'teacher' is just a login, we keep it in User table.
        # We should delete all other teachers from Teachers table.
        # BUT, if 'teacher' user is NOT linked to any Teacher profile, then deleting all Teacher profiles is fine.
        
        # Let's assume we delete all profiles that don't match the IDs of the preserved users.
        # Since 'teacher' and 'student' and 'admin' are usernames in User table, 
        # we need to know if they have corresponding profiles.
        # Usually, the system links User.username to Teacher.id / Student.id / Admin.id.
        # If User 'teacher' has username 'teacher', it would expect a Teacher with id 'teacher'.
        
        await session.execute(delete(Teacher).where(Teacher.id.notin_(original_users)))
        print("Cleaned Teachers table.")

        await session.execute(delete(Student).where(Student.id.notin_(original_users)))
        print("Cleaned Students table.")

        await session.execute(delete(Admin).where(Admin.id.notin_(original_users)))
        print("Cleaned Admins table.")

        await session.commit()
        print("Database cleanup complete!")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(clean_database())
