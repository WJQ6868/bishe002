import asyncio
import sys
import os

# Add backend to path
sys.path.append(os.getcwd())

from app.database import AsyncSessionLocal
from app.models.cert import CertLink
from sqlalchemy.future import select

async def check_cert_data():
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(CertLink))
        links = result.scalars().all()
        print(f"Found {len(links)} certificate links.")
        for link in links[:3]:
            print(f"- {link.name} ({link.category})")

if __name__ == "__main__":
    asyncio.run(check_cert_data())
