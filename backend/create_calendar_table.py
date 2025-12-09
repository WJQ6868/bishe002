import asyncio
import sys
import os

# Add backend to path
sys.path.append(os.getcwd())

from app.database import engine, Base
from app.models.calendar import CalendarEvent

async def create_tables():
    print("Creating calendar_event table...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Table created successfully.")

if __name__ == "__main__":
    asyncio.run(create_tables())
