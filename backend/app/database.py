import os
import sys
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

# 兼容在无系统安装依赖的环境下运行，将本仓库的 site-packages 注入 sys.path
_base_dir = os.path.dirname(os.path.dirname(__file__))
_paths = [
    os.path.join(_base_dir, "venv", "Lib", "site-packages"),
    os.path.join(_base_dir, "Lib", "site-packages"),
]
for _p in _paths:
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)

# SQLite 配置：优先使用项目根目录的 edu_system.db，其次后端目录
_proj_root = os.path.dirname(_base_dir)
_candidates = [
    os.path.join(_proj_root, "edu_system.db"),
    os.path.join(_base_dir, "edu_system.db"),
]
_db_path = next((p for p in _candidates if os.path.exists(p)), _candidates[-1])
_db_path_url = os.path.abspath(_db_path).replace("\\", "/")
DATABASE_URL = f"sqlite+aiosqlite:///{_db_path_url}"

# 异步引擎配置
engine = create_async_engine(
    DATABASE_URL,
    echo=True,
)

AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
