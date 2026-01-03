import asyncio
import json
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from backend.app.main import app
from backend.app.database import Base
from backend.app.models.ai_config import AiModelApi, AiWorkflowApp
from backend.app.routers import ai_qa as ai_qa_router


@pytest.fixture
async def test_db():
    """Provide an in-memory SQLite DB and seed minimal data."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False, future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    SessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with SessionLocal() as session:
            yield session

    # override dependency
    app.dependency_overrides[
        __import__("backend.app.database", fromlist=["get_db"]).get_db
    ] = override_get_db

    # seed data
    async with SessionLocal() as session:
        model = AiModelApi(
            name="测试模型",
            provider="dashscope_openai",
            model_name="qwen-plus",
            endpoint="https://dummy.endpoint",
            api_key="test-key",
            timeout_seconds=30,
            quota_per_hour=0,
            enabled=True,
            is_default=True,
        )
        session.add(model)
        await session.flush()
        app_obj = AiWorkflowApp(
            code="customer_service",
            name="AI客服",
            type="customer_service",
            status="enabled",
            model_api_id=model.id,
        )
        session.add(app_obj)
        await session.commit()

    # mock completion to return hello
    async def fake_completion(m, q, timeout=15.0):
        return "hello"
    monkeypatch.setattr(ai_qa_router, "_completion_async", fake_completion)
    yield
    # cleanup
    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.mark.anyio
async def test_customer_service_stream_returns_data(monkeypatch, test_db):
    """Ensure客服流接口能返回流式内容而不为空。"""

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/ai_qa/customer-service/stream",
            json={"user_id": "1", "question": "你好", "history_flag": True},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("content") == "hello"
