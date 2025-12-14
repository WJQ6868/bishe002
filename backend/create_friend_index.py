"""
创建好友系统数据库索引
用于在现有数据库上添加好友系统表和索引
"""
import asyncio
from sqlalchemy import text
from app.database import engine

async def create_friend_tables_and_indexes():
    """从SQL文件创建好友系统表和索引"""
    async with engine.begin() as conn:
        print("Creating friend system tables and indexes...")
        
        # 读取SQL文件
        with open('init_friend_db.sql', 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        # 分割SQL语句并执行
        statements = [s.strip() for s in sql_content.split(';') if s.strip() and not s.strip().startswith('--')]
        
        for statement in statements:
            if statement:
                try:
                    await conn.execute(text(statement))
                    print(f"✓ Executed: {statement[:50]}...")
                except Exception as e:
                    print(f"✗ Error executing statement: {e}")
                    print(f"  Statement: {statement[:100]}...")
        
        print("Friend system tables and indexes created successfully!")

if __name__ == "__main__":
    asyncio.run(create_friend_tables_and_indexes())
