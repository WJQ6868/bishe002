from __future__ import annotations

import asyncio
import json
import logging
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
logger = logging.getLogger(__name__)

SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}


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


def _make_sse_payload(content: str, kind: str = "answer") -> str:
    return f"data: {json.dumps({'type': kind, 'content': content}, ensure_ascii=False)}\n\n"


def _thinking_steps(kb_ids: List[int]) -> List[str]:
    steps: List[str] = []
    if kb_ids:
        steps.append("正在检索知识库片段")
        steps.append("正在整理检索结果")
    else:
        steps.append("正在分析问题")
    steps.append("正在生成回答")
    return steps


def _extract_non_stream_text(provider: str, body: str) -> str:
    text = (body or "").strip()
    if not text:
        return ""
    try:
        data = json.loads(text)
    except Exception:
        return text

    if provider == "dashscope_openai":
        return (
            data.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
            or text
        )

    if provider == "ark_responses":
        output = data.get("output") or data.get("data") or []
        if isinstance(output, list) and output:
            contents = output[0].get("content") if isinstance(output[0], dict) else None
            if isinstance(contents, list) and contents:
                value = contents[0].get("text", "") or contents[0].get("output_text", "")
                if value:
                    return value
        return data.get("output_text") or data.get("message") or text

    return text


def _extract_stream_text(payload: str) -> str:
    if not payload or payload == "[DONE]":
        return ""
    try:
        data = json.loads(payload)
    except Exception:
        return payload

    if not isinstance(data, dict):
        return str(data)

    choices = data.get("choices")
    if isinstance(choices, list) and choices:
        choice = choices[0] or {}
        delta = choice.get("delta") or choice.get("message") or {}
        if isinstance(delta, dict):
            content = delta.get("content") or delta.get("text")
            if content:
                return str(content)

    for key in ("output_text", "content", "message", "text"):
        value = data.get(key)
        if isinstance(value, str) and value:
            return value
        if isinstance(value, dict):
            inner = value.get("content") or value.get("text")
            if isinstance(inner, str) and inner:
                return inner

    output = data.get("output") or data.get("data")
    if isinstance(output, list) and output:
        first = output[0]
        if isinstance(first, dict):
            contents = first.get("content")
            if isinstance(contents, list) and contents:
                item = contents[0]
                if isinstance(item, dict):
                    inner = item.get("text") or item.get("output_text")
                    if isinstance(inner, str) and inner:
                        return inner

    return ""


async def _iter_sse_events(response: httpx.Response) -> AsyncGenerator[str, None]:
    buffer: List[str] = []
    async for line in response.aiter_lines():
        if not line:
            if buffer:
                yield "\n".join(buffer)
                buffer = []
            continue
        if line.startswith("data:"):
            buffer.append(line[5:].strip())
    if buffer:
        yield "\n".join(buffer)


def _describe_upstream_exception(exc: Exception) -> str:
    if isinstance(exc, httpx.ReadTimeout):
        return "上游模型响应超时，请稍后重试或在管理端适当提高超时时间"
    if isinstance(exc, httpx.ConnectTimeout):
        return "连接模型服务超时，请检查网络连通性或模型接口地址"
    if isinstance(exc, httpx.ConnectError):
        return "连接模型服务失败，请检查 endpoint、网络或代理配置"
    if isinstance(exc, httpx.RemoteProtocolError):
        return "模型服务连接被中断，请稍后重试"
    if isinstance(exc, httpx.HTTPError):
        detail = str(exc).strip()
        return f"{type(exc).__name__}: {detail}" if detail else f"{type(exc).__name__}"
    detail = str(exc).strip()
    return f"{type(exc).__name__}: {detail}" if detail else f"{type(exc).__name__}"


async def _post_json_with_retry(
    client: httpx.AsyncClient,
    url: str,
    *,
    payload: dict,
    headers: dict,
    max_attempts: int = 2,
) -> httpx.Response:
    last_exc: Optional[Exception] = None
    for attempt in range(1, max_attempts + 1):
        try:
            return await client.post(url, json=payload, headers=headers)
        except (httpx.TimeoutException, httpx.ConnectError, httpx.ReadError, httpx.WriteError, httpx.RemoteProtocolError) as exc:
            last_exc = exc
            logger.warning(
                "AI upstream request failed on attempt %s/%s: %r",
                attempt,
                max_attempts,
                exc,
            )
            if attempt >= max_attempts:
                raise
            await asyncio.sleep(min(1.2 * attempt, 2.0))
    if last_exc:
        raise last_exc
    raise RuntimeError("AI upstream request failed without a captured exception")


async def _call_model_api(model: AiModelApi, prompt: str) -> AsyncGenerator[str, None]:
    provider = (model.provider or "").strip().lower()
    endpoint = (model.endpoint or "").strip().rstrip("/")
    model_name = (model.model_name or "").strip()
    api_key = (model.api_key or "").strip()
    if not endpoint or not model_name or not api_key:
        yield _make_sse_payload("AI 模型未完整配置，请在管理端补全 API Key/Endpoint/模型名称")
        return

    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
    headers.update(_parse_api_header(model.api_header))

    timeout_seconds = int(model.timeout_seconds or 0)
    if timeout_seconds < 60:
        timeout_seconds = 60
    timeout = httpx.Timeout(timeout_seconds, connect=min(15.0, float(timeout_seconds)), write=min(30.0, float(timeout_seconds)))
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            if provider == "dashscope_openai":
                payload = {
                    "model": model_name,
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": True,
                }
                if model.temperature is not None:
                    payload["temperature"] = model.temperature
                if model.max_output_tokens is not None:
                    payload["max_tokens"] = model.max_output_tokens
                async with client.stream(
                    "POST",
                    f"{endpoint}/chat/completions",
                    json=payload,
                    headers={**headers, "Accept": "text/event-stream"},
                ) as resp:
                    if resp.status_code < 200 or resp.status_code >= 300:
                        body = (await resp.aread()).decode("utf-8", errors="ignore")
                        msg = f"AI 接口请求失败: HTTP {resp.status_code} {body[:200]}"
                        yield _make_sse_payload(msg)
                        return
                    content_type = resp.headers.get("content-type", "")
                    if "text/event-stream" in content_type:
                        async for raw in _iter_sse_events(resp):
                            if raw == "[DONE]":
                                break
                            chunk = _extract_stream_text(raw)
                            if chunk:
                                yield _make_sse_payload(chunk)
                        return

                    body = (await resp.aread()).decode("utf-8", errors="ignore")
                    output_text = _extract_non_stream_text(provider, body)
                    for piece in _split_text(output_text):
                        yield _make_sse_payload(piece)
                    return

            if provider == "ark_responses":
                payload = {
                    "model": model_name,
                    "stream": True,
                    "input": [{"role": "user", "content": [{"type": "input_text", "text": prompt}]}],
                }
                if model.temperature is not None:
                    payload["temperature"] = model.temperature
                async with client.stream(
                    "POST",
                    f"{endpoint}/responses",
                    json=payload,
                    headers={**headers, "Accept": "text/event-stream"},
                ) as resp:
                    if resp.status_code < 200 or resp.status_code >= 300:
                        body = (await resp.aread()).decode("utf-8", errors="ignore")
                        msg = f"AI 接口请求失败: HTTP {resp.status_code} {body[:200]}"
                        yield _make_sse_payload(msg)
                        return
                    content_type = resp.headers.get("content-type", "")
                    if "text/event-stream" in content_type:
                        async for raw in _iter_sse_events(resp):
                            if raw == "[DONE]":
                                break
                            chunk = _extract_stream_text(raw)
                            if chunk:
                                yield _make_sse_payload(chunk)
                        return

                    body = (await resp.aread()).decode("utf-8", errors="ignore")
                    output_text = _extract_non_stream_text(provider, body)
                    for piece in _split_text(output_text):
                        yield _make_sse_payload(piece)
                    return

            yield _make_sse_payload("不支持的模型 provider，请在管理端检查配置")
            return
    except Exception as e:
        logger.exception("AI upstream request raised an exception")
        yield _make_sse_payload(f"AI 请求异常: {_describe_upstream_exception(e)}")


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
            for step in _thinking_steps(kb_ids):
                yield _make_sse_payload(step, "thinking")
            async for chunk in _call_model_api(model, prompt):
                yield chunk

        return StreamingResponse(gen(), media_type="text/event-stream", headers=SSE_HEADERS)

    if ai_client.api_key:
        async def gen_qwen():
            for step in _thinking_steps(kb_ids):
                yield _make_sse_payload(step, "thinking")
            for chunk in ai_client.call_stream_api(request.user_id, prompt, request.history_flag):
                yield chunk

        return StreamingResponse(
            gen_qwen(),
            media_type="text/event-stream",
            headers=SSE_HEADERS,
        )

    async def gen_err():
        yield _make_sse_payload("AI 模型未配置，请在管理端配置并启用模型")

    return StreamingResponse(gen_err(), media_type="text/event-stream", headers=SSE_HEADERS)
