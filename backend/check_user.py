import asyncio
import sys
import os

# Add backend to path
sys.path.append(os.getcwd())

from app.database import AsyncSessionLocal
from app.models.user import User
from sqlalchemy.future import select

async def check_user():
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.username == "800001"))
        user = result.scalars().first()
        if user:
            print(f"User found: ID={user.id}, Username={user.username}, Role={user.role}")
        else:
            print("User 800001 NOT found!")

        # List all users
        print("\nAll users:")
        result = await session.execute(select(User))
        users = result.scalars().all()
        for u in users:
            print(f"- {u.username} ({u.role})")

if __name__ == "__main__":
    asyncio.run(check_user())
