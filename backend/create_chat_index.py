import asyncio
from sqlalchemy import text
from app.database import engine

async def create_chat_index():
    async with engine.begin() as conn:
        # Check if index exists
        # Note: In SQLite, "IF NOT EXISTS" is supported in CREATE INDEX
        print("Creating index on chat_message(from_id, to_id)...")
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_chat_from_to ON chat_message(from_id, to_id)"))
        print("Index created successfully.")

if __name__ == "__main__":
    asyncio.run(create_chat_index())
