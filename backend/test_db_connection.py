import asyncio
import os
import sys
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

# 模拟 database.py 的路径逻辑
current_dir = os.path.dirname(os.path.abspath(__file__))
# backend/app -> backend
base_dir = current_dir
# backend -> project_root
proj_root = os.path.dirname(base_dir)

print(f"Current Dir: {current_dir}")
print(f"Base Dir (Backend): {base_dir}")
print(f"Project Root: {proj_root}")

candidates = [
    os.path.join(proj_root, "edu_system.db"),
    os.path.join(base_dir, "edu_system.db"),
]

db_path = next((p for p in candidates if os.path.exists(p)), None)

if not db_path:
    print("❌ Error: edu_system.db not found in candidates:")
    for p in candidates:
        print(f"  - {p}")
    sys.exit(1)

print(f"✅ Found database at: {db_path}")

db_path_url = os.path.abspath(db_path).replace("\\", "/")
DATABASE_URL = f"sqlite+aiosqlite:///{db_path_url}"

print(f"Connecting to: {DATABASE_URL}")

async def test_connection():
    try:
        engine = create_async_engine(DATABASE_URL, echo=False)
        async with engine.connect() as conn:
            # 测试1: 简单连接
            result = await conn.execute(text("SELECT 1"))
            print("✅ Connection successful! SELECT 1 returned:", result.scalar())
            
            # 测试2: 检查表是否存在
            print("Checking tables...")
            tables_res = await conn.execute(text("SELECT name FROM sqlite_master WHERE type='table';"))
            tables = [row[0] for row in tables_res.fetchall()]
            print("Existing tables:", tables)
            
            required_tables = ['students', 'teachers', 'admins', 'sys_users', 'user_profiles']
            missing = [t for t in required_tables if t not in tables]
            
            if missing:
                print(f"⚠️ Warning: Missing tables: {missing}")
            else:
                print("✅ All required tables (students, teachers, admins, sys_users, user_profiles) found.")

            # 测试3: 读取数据条数
            for t in ['students', 'teachers']:
                if t in tables:
                    count_res = await conn.execute(text(f"SELECT count(*) FROM {t}"))
                    count = count_res.scalar()
                    print(f"📊 Table '{t}' has {count} rows.")
                    
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        # Check for aiosqlite
        try:
            import aiosqlite
            print("aiosqlite is installed.")
        except ImportError:
            print("❌ aiosqlite is NOT installed. Please run: pip install aiosqlite")

if __name__ == "__main__":
    asyncio.run(test_connection())
