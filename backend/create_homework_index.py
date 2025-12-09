import asyncio
import sys
import os

# Add the current directory to sys.path to ensure imports work
sys.path.append(os.getcwd())

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.database import DATABASE_URL

# Create async engine
engine = create_async_engine(
    DATABASE_URL,
    echo=True,
    future=True,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
)

async def create_index():
    async with engine.begin() as conn:
        print("Creating index idx_homework_submit on homework_submit(homework_id)...")
        try:
            await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_homework_submit ON homework_submit(homework_id)"))
            print("Index created successfully.")
        except Exception as e:
            print(f"Error creating index: {e}")

if __name__ == "__main__":
    asyncio.run(create_index())
