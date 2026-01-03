import json

import re
import httpx

from typing import Generator, List, Optional



from fastapi import APIRouter, Depends, HTTPException

from fastapi.responses import StreamingResponse

from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy.future import select



from ..database import get_db

from ..models.ai_config import (

    AiKnowledgeBase,

    AiModelApi,

    AiWorkflowApp,

    StudentCourseAiSelection,

)

from ..schemas.ai import QARequest

from ..services.ai_service import ArkResponsesClient, DashscopeOpenAIClient

from ..services.ai_workflow import retrieve_top_chunks



router = APIRouter(prefix="/ai_qa", tags=["AI QA"])



_dashscope_client = DashscopeOpenAIClient()
_ark_client = ArkResponsesClient()

def _model_api_ready(model: Optional[AiModelApi]) -> bool:
    if not model:
        return False
    key = (getattr(model, "api_key", "") or "").strip()
    return key not in {"", "__PLEASE_SET__", "__PLACEHOLDER__"}

async def _get_default_enabled_model(db: AsyncSession) -> AiModelApi | None:

    res = await db.execute(

        select(AiModelApi)

        .where(AiModelApi.enabled == True)

        .order_by(AiModelApi.is_default.desc(), AiModelApi.id.desc())

    )

    return res.scalars().first()





def _sse_single_message(text: str) -> Generator[str, None, None]:

    payload = json.dumps({"content": text}, ensure_ascii=False)

    yield f"data: {payload}\n\n"





def _pick_generator(

    *,

    provider: str | None,

    model_name: str | None,

    endpoint: str | None,

    api_key: str | None,

    user_id: str,

    question: str,

    history_flag: bool,

) -> Generator[str, None, None]:

    provider_key = (provider or "").strip()

    endpoint_url = (endpoint or "").strip()

    api_key_val = (api_key or "").strip()

    model = (model_name or "").strip()



    if provider_key == "ark_responses":

        return _ark_client.call_stream_api(

            user_id=user_id,

            question=question,

            history_flag=history_flag,

            api_key=api_key_val or None,

            base_url=endpoint_url or None,

            model=model or None,

        )

    return _dashscope_client.call_stream_api(

        user_id,

        question,

        history_flag,

        api_key=api_key_val or None,

        base_url=endpoint_url or None,

        model=model or None,

    )





def _safe_int(s: str) -> int | None:

    try:

        return int(str(s))

    except Exception:

        return None





def _tokenize(text: str) -> list[str]:

    parts = re.split(r"[^0-9A-Za-z\u4e00-\u9fff]+", text or "")

    words = [p.strip() for p in parts if p and len(p.strip()) >= 2]

    # 去重但保持顺?

    seen = set()

    out: list[str] = []

    for w in words:

        if w in seen:

            continue

        seen.add(w)

        out.append(w)

    return out[:12]





def _read_text_file(abs_path: str) -> str:

    try:

        with open(abs_path, "rb") as f:

            data = f.read()

        return data.decode("utf-8", errors="ignore")

    except Exception:

        return ""





def _extract_text(abs_path: str, ext: str) -> str:

    ext = (ext or "").lower()

    if ext in {".txt", ".md"}:

        return _read_text_file(abs_path)



    # 可选支持：pdf/docx（依赖可能未安装，失败则回退空文本）

    if ext == ".pdf":

        try:

            from pypdf import PdfReader  # type: ignore



            reader = PdfReader(abs_path)

            chunks = []

            for page in reader.pages[:10]:

                chunks.append(page.extract_text() or "")

            return "\n".join(chunks)

        except Exception:

            return ""



    if ext == ".docx":

        try:

            import docx  # type: ignore



            d = docx.Document(abs_path)

            return "\n".join(p.text for p in d.paragraphs if p.text)

        except Exception:

            return ""



    # .doc 等暂不解?

    return ""





def _build_snippet(text: str, keywords: list[str], max_len: int = 800) -> str:

    if not text:

        return ""

    lower = text.lower()

    hit_pos = None

    for kw in keywords:

        pos = lower.find(kw.lower())

        if pos != -1:

            hit_pos = pos

            break

    if hit_pos is None:

        return (text[:max_len]).strip()

    start = max(0, hit_pos - 200)

    end = min(len(text), hit_pos + max_len)

    return (text[start:end]).strip()





def _customer_service_default_settings() -> dict:
    return {
        "welcome_str": "你好，我是AI客服，可以帮你解答校园常见问题。",
        "recommend_questions": ["如何请假？", "如何选课？", "成绩在哪里查询？"],
        "search_placeholder": "请输入问题，例如：如何请假？",
        "system_prompt_template": "你是校园教务系统的AI客服。请优先依据知识库片段回答，并在相关句子后用【序号】标注引用；若知识库不足，请明确说明并给出可执行建议。",
    }






def _normalize_customer_service_settings(data: dict) -> dict:

    base = _customer_service_default_settings()

    if not isinstance(data, dict):

        return base

    out = {**base, **data}

    if not isinstance(out.get("welcome_str"), str):

        out["welcome_str"] = base["welcome_str"]

    if not isinstance(out.get("search_placeholder"), str):

        out["search_placeholder"] = base["search_placeholder"]

    rq = out.get("recommend_questions")

    if not isinstance(rq, list):

        out["recommend_questions"] = base["recommend_questions"]

    else:

        out["recommend_questions"] = [str(x).strip() for x in rq if str(x).strip()][:12]

    spt = out.get("system_prompt_template")

    if spt is None:

        out["system_prompt_template"] = base["system_prompt_template"]

    elif not isinstance(spt, str):

        out["system_prompt_template"] = base["system_prompt_template"]

    return out





def _load_json_settings(settings_json: Optional[str]) -> dict:

    if not settings_json:

        return {}

    try:

        data = json.loads(settings_json)

        if isinstance(data, dict):

            return data

    except Exception:

        pass

    return {}





async def _get_or_create_app(

    db: AsyncSession,

    *,

    code: str,

    name: str,

    app_type: str,

) -> AiWorkflowApp:

    app = (await db.execute(select(AiWorkflowApp).where(AiWorkflowApp.code == code))).scalars().first()

    if app:

        return app

    app = AiWorkflowApp(code=code, name=name, type=app_type, status="enabled")

    db.add(app)

    await db.commit()

    await db.refresh(app)

    return app





async def _resolve_course_kb_ids(db: AsyncSession, course_id: Optional[int]) -> List[int]:

    if not course_id:

        return []

    res = await db.execute(

        select(AiKnowledgeBase.id)

        .where(AiKnowledgeBase.course_id == course_id)

        .order_by(AiKnowledgeBase.updated_at.desc().nullslast(), AiKnowledgeBase.id.desc())

    )

    return [int(row[0]) for row in res.all()]





async def _build_kb_prompt(

    db: AsyncSession,

    kb_ids: List[int],

    question: str,

    heading: str,

) -> str:

    chunks = await retrieve_top_chunks(db, kb_ids, question, limit=8)

    if not chunks:

        return ""

    lines: List[str] = []

    lines.append(heading)

    for idx, (chunk, _score) in enumerate(chunks, start=1):

        title = chunk.document_title or "知识片段"

        lines.append(f"【{idx}】{title}\n{chunk.content.strip()}")

    return "\n".join(lines)





def _compose_prompt(question: str, system_prompt: Optional[str], kb_context: str) -> str:

    blocks: List[str] = []

    if system_prompt:

        blocks.append(system_prompt.strip())

    if kb_context:

        blocks.append(kb_context.strip())

    blocks.append(f"用户问题：{question.strip()}")

    return "\n\n".join(blocks)


def _with_fallback(gen: Generator[str, None, None], fallback_text: str) -> Generator[str, None, None]:
    """Ensure at least one SSE chunk is sent even if upstream yields nothing."""
    yielded = False
    for chunk in gen:
        yielded = True
        yield chunk
    if not yielded:
        for chunk in _sse_single_message(fallback_text):
            yield chunk


def _with_leading_notice(gen: Generator[str, None, None], notice: str, fallback: str) -> Generator[str, None, None]:
    """Send a leading notice chunk, then stream generator with fallback."""
    for chunk in _sse_single_message(notice):
        yield chunk
    for chunk in _with_fallback(gen, fallback):
        yield chunk


def _call_completion(model: AiModelApi, question: str, timeout: float = 15.0) -> str:
    """Fallback: 同步单轮补偿调用，避免流式无输出"""
    provider = (model.provider or "").strip()
    endpoint = (model.endpoint or "").strip().rstrip("/")
    api_key = (model.api_key or "").strip()
    model_name = (model.model_name or "").strip()
    if not provider or not endpoint or not api_key or not model_name:
        return ""
    try:
        if provider == "dashscope_openai":
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            resp = httpx.post(
                f"{endpoint}/chat/completions",
                json={
                    "model": model_name,
                    "messages": [{"role": "user", "content": question}],
                    "stream": False,
                },
                headers=headers,
                timeout=timeout,
            )
            if resp.status_code >= 200 and resp.status_code < 300:
                data = resp.json()
                return (
                    data.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "")
                )
            return f"模型补偿调用失败: HTTP {resp.status_code}"
        if provider == "ark_responses":
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            resp = httpx.post(
                f"{endpoint}/responses",
                json={
                    "model": model_name,
                    "stream": False,
                    "input": [{"role": "user", "content": [{"type": "input_text", "text": question}]}],
                },
                headers=headers,
                timeout=timeout,
            )
            if resp.status_code >= 200 and resp.status_code < 300:
                data = resp.json()
                out = data.get("output") or data.get("data") or []
                if isinstance(out, list) and out:
                    contents = out[0].get("content") if isinstance(out[0], dict) else None
                    if isinstance(contents, list) and contents:
                        return contents[0].get("text", "") or contents[0].get("output_text", "")
                return data.get("message", "") or ""
            return f"模型补偿调用失败: HTTP {resp.status_code}"
    except Exception:
        return ""
    return ""


def _with_completion(gen: Generator[str, None, None], model: Optional[AiModelApi], question: str, fallback_text: str) -> Generator[str, None, None]:
    """优先流式，若一条未产出，则走一次非流式补偿，再兜底提示"""
    yielded = False
    for chunk in gen:
        yielded = True
        yield chunk
    if yielded:
        return
    if model:
        text = _call_completion(model, question)
        if text:
            for chunk in _sse_single_message(text):
                yield chunk
            return
    for chunk in _sse_single_message(fallback_text):
        yield chunk


async def _completion_async(model: AiModelApi, question: str, timeout: float = 15.0) -> str:
    provider = (model.provider or "").strip()
    endpoint = (model.endpoint or "").strip().rstrip("/")
    api_key = (model.api_key or "").strip()
    model_name = (model.model_name or "").strip()
    if not provider or not endpoint or not api_key or not model_name:
        return ""
    try:
        if provider == "dashscope_openai":
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(
                    f"{endpoint}/chat/completions",
                    json={
                        "model": model_name,
                        "messages": [{"role": "user", "content": question}],
                        "stream": False,
                    },
                    headers=headers,
                )
            if 200 <= resp.status_code < 300:
                data = resp.json()
                return (
                    data.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "")
                )
            return ""
        if provider == "ark_responses":
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(
                    f"{endpoint}/responses",
                    json={
                        "model": model_name,
                        "stream": False,
                        "input": [{"role": "user", "content": [{"type": "input_text", "text": question}]}],
                    },
                    headers=headers,
                )
            if 200 <= resp.status_code < 300:
                data = resp.json()
                out = data.get("output") or data.get("data") or []
                if isinstance(out, list) and out:
                    contents = out[0].get("content") if isinstance(out[0], dict) else None
                    if isinstance(contents, list) and contents:
                        return contents[0].get("text", "") or contents[0].get("output_text", "")
                return data.get("message", "") or ""
            return ""
    except Exception:
        return ""
    return ""





async def _resolve_model_api(

    db: AsyncSession,

    *,

    explicit_key: Optional[str],

    app: Optional[AiWorkflowApp],

) -> Optional[AiModelApi]:

    model_key = (explicit_key or "").strip()

    if model_key.startswith("db:"):

        mid = _safe_int(model_key.split(":", 1)[1])

        if mid is not None:

            obj = (

                await db.execute(select(AiModelApi).where(AiModelApi.id == mid, AiModelApi.enabled == True))

            ).scalars().first()

            if obj:

                return obj

    if app and app.model_api_id:

        obj = (

            await db.execute(

                select(AiModelApi).where(AiModelApi.id == int(app.model_api_id), AiModelApi.enabled == True)

            )

        ).scalars().first()

        if obj:

            return obj

    return await _get_default_enabled_model(db)





async def _load_customer_service_settings(db: AsyncSession) -> dict:

    app = await _get_or_create_app(db, code="customer_service", name="AI客服", app_type="customer_service")

    payload = _load_json_settings(app.settings_json)

    return _normalize_customer_service_settings(payload)





@router.post("/qa/stream")
async def stream_qa(request: QARequest, db: AsyncSession = Depends(get_db)):
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    # 先按 workflow 指定的课程助手工作流；否则退回默认课程助手
    app_code = (request.workflow or "").strip()
    if app_code.startswith("app:"):
        app_code = app_code[4:]
    app: AiWorkflowApp | None = None
    if app_code:
        stmt = select(AiWorkflowApp).where(
            AiWorkflowApp.code == app_code,
            AiWorkflowApp.type == "course_assistant",
            AiWorkflowApp.status == "enabled",
        )
        if request.course_id is not None:
            stmt = stmt.where((AiWorkflowApp.course_id == request.course_id) | (AiWorkflowApp.course_id == None))
        app = (await db.execute(stmt)).scalars().first()
    if not app:
        app = await _get_or_create_app(db, code="course_assistant", name="AI课程助手", app_type="course_assistant")

    app_settings = _load_json_settings(app.settings_json)

    # 优先使用学生课程自选模型
    selected_model: AiModelApi | None = None
    if request.course_id is not None:
        uid = _safe_int(request.user_id)
        if uid is not None:
            sel = (
                await db.execute(
                    select(StudentCourseAiSelection).where(
                        StudentCourseAiSelection.student_user_id == uid,
                        StudentCourseAiSelection.course_id == request.course_id,
                    )
                )
            ).scalars().first()
            if sel and sel.model_api_id:
                selected_model = (
                    await db.execute(
                        select(AiModelApi).where(AiModelApi.id == sel.model_api_id, AiModelApi.enabled == True)
                    )
                ).scalars().first()

    if not _model_api_ready(selected_model):
        selected_model = await _resolve_model_api(db, explicit_key=request.model, app=app)

    if not _model_api_ready(selected_model):
        gen = _sse_single_message("AI 课程助手未配置可用模型或缺少 API Key，请在后台启用并填写密钥。")
        return StreamingResponse(gen, media_type="text/event-stream")

    kb_ids: List[int] = []
    if app.knowledge_base_id:
        kb_ids.append(int(app.knowledge_base_id))
    kb_ids.extend(await _resolve_course_kb_ids(db, request.course_id))
    kb_context = await _build_kb_prompt(
        db,
        kb_ids,
        request.question,
        "以下为可能有帮助的知识库片段（根据相关度排序）：",
    )
    system_prompt = app_settings.get("system_prompt_template") or "你是课程智能助手，请基于知识片段回答，并引用编号。"
    final_question = _compose_prompt(request.question, system_prompt, kb_context)

    if selected_model:
        gen = _pick_generator(
            provider=selected_model.provider,
            model_name=selected_model.model_name,
            endpoint=selected_model.endpoint,
            api_key=selected_model.api_key,
            user_id=request.user_id,
            question=final_question,
            history_flag=request.history_flag,
        )
    else:
        gen = _dashscope_client.call_stream_api(request.user_id, final_question, request.history_flag)

    try:
        return StreamingResponse(
            _with_completion(gen, selected_model, final_question, "AI 课程助手未返回内容，请检查模型连通性或稍后重试。"),
            media_type="text/event-stream",
        )
    except Exception as e:
        err = _sse_single_message(f"AI 课程助手调用失败: {e}")
        return StreamingResponse(err, media_type="text/event-stream")

@router.post("/customer-service/stream")
async def stream_customer_service(request: QARequest, db: AsyncSession = Depends(get_db)):
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    # workflow 优先：app:{code} 或直接 code
    app_code = (request.workflow or "").strip() or (request.model or "").strip()
    if app_code.startswith("app:"):
        app_code = app_code[4:]

    app: AiWorkflowApp | None = None
    if app_code:
        app = (
            await db.execute(
                select(AiWorkflowApp).where(
                    AiWorkflowApp.code == app_code,
                    AiWorkflowApp.type == "customer_service",
                    AiWorkflowApp.status == "enabled",
                )
            )
        ).scalars().first()
    if not app:
        app = await _get_or_create_app(db, code="customer_service", name="AI客服", app_type="customer_service")

    settings = _normalize_customer_service_settings(_load_json_settings(app.settings_json))
    selected_model = await _resolve_model_api(db, explicit_key=request.model, app=app)

    if not _model_api_ready(selected_model):
        gen = _sse_single_message("AI 客服未配置可用模型或缺少 API Key，请在后台启用并填写密钥。")
        return StreamingResponse(gen, media_type="text/event-stream")

    kb_ids: List[int] = []
    if app.knowledge_base_id:
        kb_ids.append(int(app.knowledge_base_id))
    kb_ids.extend(await _resolve_course_kb_ids(db, request.course_id))
    kb_context = await _build_kb_prompt(
        db,
        kb_ids,
        request.question,
        "以下是客服知识库片段，请优先引用（并标注编号）：",
    )
    system_prompt = settings.get("system_prompt_template") or "你是校园教务 AI 客服，请引用知识库回答，无法覆盖时说明并提供建议。"
    final_question = _compose_prompt(request.question, system_prompt, kb_context)

    # 改为非流式直接返回文本
    text = await _completion_async(selected_model, final_question)
    if not text:
        return {"content": "", "message": "AI 客服未返回内容，请检查模型连通性或稍后重试。"}
    return {"content": text}
