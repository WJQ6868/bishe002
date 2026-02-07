from __future__ import annotations

import json
from typing import AsyncGenerator, Optional, List

import httpx
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models.ai_config import AiModelApi, AiWorkflowApp, AiKnowledgeBase
from ..schemas.ai import QARequest
from ..services.ai_service import QwenClient
from ..services.ai_workflow import retrieve_top_chunks

router = APIRouter(prefix="/ai_qa", tags=["AI QA"])

ai_client = QwenClient()


def _parse_model_id(raw: Optional[str]) -> Optional[int]:
    if not raw:
        return None
    val = str(raw).strip()
    if not val:
        return None
    if val.startswith("db:"):
        val = val[3:]
    return int(val) if val.isdigit() else None


async def _load_workflow_app(db: AsyncSession, code: Optional[str]) -> Optional[AiWorkflowApp]:
    if not code:
        return None
    return (await db.execute(select(AiWorkflowApp).where(AiWorkflowApp.code == code))).scalars().first()


async def _resolve_model(
    db: AsyncSession,
    model_raw: Optional[str],
    app: Optional[AiWorkflowApp],
) -> Optional[AiModelApi]:
    model_id = _parse_model_id(model_raw)
    if model_id:
        obj = (
            await db.execute(
                select(AiModelApi).where(
                    AiModelApi.id == model_id,
                    AiModelApi.enabled == True,  # noqa: E712
                )
            )
        ).scalars().first()
        if obj:
            return obj

    if app and app.model_api_id:
        obj = (
            await db.execute(
                select(AiModelApi).where(
                    AiModelApi.id == app.model_api_id,
                    AiModelApi.enabled == True,  # noqa: E712
                )
            )
        ).scalars().first()
        if obj:
            return obj

    # fallback: enabled default model
    return (
        await db.execute(
            select(AiModelApi)
            .where(AiModelApi.enabled == True)  # noqa: E712
            .order_by(AiModelApi.is_default.desc(), AiModelApi.id.desc())
        )
    ).scalars().first()


async def _collect_kb_ids(
    db: AsyncSession,
    app: Optional[AiWorkflowApp],
    course_id: Optional[int],
) -> List[int]:
    ids: List[int] = []
    if app and app.knowledge_base_id:
        ids.append(int(app.knowledge_base_id))
    if course_id:
        res = await db.execute(select(AiKnowledgeBase.id).where(AiKnowledgeBase.course_id == int(course_id)))
        ids.extend([int(x) for x in res.scalars().all()])
    # de-dup
    out: List[int] = []
    for x in ids:
        if x not in out:
            out.append(x)
    return out


async def _build_prompt(db: AsyncSession, question: str, kb_ids: List[int]) -> str:
    if not kb_ids:
        return question
    try:
        chunks = await retrieve_top_chunks(db, kb_ids, question, limit=6)
    except Exception:
        return question
    if not chunks:
        return question
    lines: List[str] = []
    for idx, (chunk, _score) in enumerate(chunks, start=1):
        text = (chunk.content or "").strip()
        if text:
            lines.append(f"[{idx}] {text}")
    if not lines:
        return question
    context = "\n".join(lines)
    return f"以下是与问题相关的知识库片段，请结合回答：\n{context}\n\n问题：{question}"


def _parse_api_header(api_header: Optional[str]) -> dict:
    if not api_header:
        return {}
    try:
        data = json.loads(api_header)
    except Exception:
        return {}
    if not isinstance(data, dict):
        return {}
    return {str(k): str(v) for k, v in data.items() if v is not None}


def _split_text(text: str, size: int = 220) -> List[str]:
    if not text:
        return []
    if len(text) <= size:
        return [text]
    return [text[i : i + size] for i in range(0, len(text), size)]


async def _call_model_api(model: AiModelApi, prompt: str) -> AsyncGenerator[str, None]:
    provider = (model.provider or "").strip().lower()
    endpoint = (model.endpoint or "").strip().rstrip("/")
    model_name = (model.model_name or "").strip()
    api_key = (model.api_key or "").strip()
    if not endpoint or not model_name or not api_key:
        yield f"data: {json.dumps({'content': 'AI 模型未完整配置，请在管理端补全 API Key/Endpoint/模型名称'}, ensure_ascii=False)}\n\n"
        return

    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
    headers.update(_parse_api_header(model.api_header))

    timeout = httpx.Timeout(model.timeout_seconds or 30)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            if provider == "dashscope_openai":
                payload = {
                    "model": model_name,
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False,
                }
                if model.temperature is not None:
                    payload["temperature"] = model.temperature
                if model.max_output_tokens is not None:
                    payload["max_tokens"] = model.max_output_tokens
                resp = await client.post(f"{endpoint}/chat/completions", json=payload, headers=headers)
            elif provider == "ark_responses":
                payload = {
                    "model": model_name,
                    "stream": False,
                    "input": [{"role": "user", "content": [{"type": "input_text", "text": prompt}]}],
                }
                if model.temperature is not None:
                    payload["temperature"] = model.temperature
                resp = await client.post(f"{endpoint}/responses", json=payload, headers=headers)
            else:
                yield f"data: {json.dumps({'content': '不支持的模型 provider，请在管理端检查配置'}, ensure_ascii=False)}\n\n"
                return

        if resp.status_code < 200 or resp.status_code >= 300:
            msg = f"AI 接口请求失败: HTTP {resp.status_code} {resp.text[:200]}"
            yield f"data: {json.dumps({'content': msg}, ensure_ascii=False)}\n\n"
            return

        output_text = ""
        try:
            data = resp.json()
            if provider == "dashscope_openai":
                output_text = (
                    data.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "")
                )
            elif provider == "ark_responses":
                output = data.get("output") or data.get("data") or []
                if isinstance(output, list) and output:
                    contents = output[0].get("content") if isinstance(output[0], dict) else None
                    if isinstance(contents, list) and contents:
                        output_text = contents[0].get("text", "") or contents[0].get("output_text", "")
                if not output_text and isinstance(data, dict):
                    output_text = data.get("output_text") or data.get("message", "") or ""
        except Exception:
            output_text = ""

        if not output_text:
            output_text = (resp.text or "").strip()

        for piece in _split_text(output_text):
            yield f"data: {json.dumps({'content': piece}, ensure_ascii=False)}\n\n"
    except Exception as e:
        yield f"data: {json.dumps({'content': f'AI 请求异常: {e}'}, ensure_ascii=False)}\n\n"


@router.post("/qa/stream")
async def stream_qa(request: QARequest, db: AsyncSession = Depends(get_db)):
    question = (request.question or "").strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    app = await _load_workflow_app(db, request.workflow)
    model = await _resolve_model(db, request.model, app)
    kb_ids = await _collect_kb_ids(db, app, request.course_id)
    prompt = await _build_prompt(db, question, kb_ids)

    if model:
        async def gen():
            async for chunk in _call_model_api(model, prompt):
                yield chunk

        return StreamingResponse(gen(), media_type="text/event-stream")

    if ai_client.api_key:
        return StreamingResponse(
            ai_client.call_stream_api(request.user_id, prompt, request.history_flag),
            media_type="text/event-stream",
        )

    async def gen_err():
        yield f"data: {json.dumps({'content': 'AI 模型未配置，请在管理端配置并启用模型'}, ensure_ascii=False)}\n\n"

    return StreamingResponse(gen_err(), media_type="text/event-stream")
