from app.database import engine, Base
from app.models.user import User, UserProfile
from app.models.student import Student
from app.models.course import Teacher
from app.models.admin import Admin
import asyncio

async def reset_db():
    async with engine.begin() as conn:
        print("Dropping tables...")
        # Drop specific tables to force recreation with correct schema
        await conn.run_sync(Base.metadata.drop_all, tables=[
            User.__table__, UserProfile.__table__, 
            Student.__table__, Teacher.__table__, Admin.__table__
        ])
        print("Creating tables...")
        await conn.run_sync(Base.metadata.create_all)
    print("Database reset complete.")

if __name__ == "__main__":
    asyncio.run(reset_db())
