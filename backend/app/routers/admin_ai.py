from __future__ import annotations

import json
import os
import re
import uuid
from typing import List, Optional

import httpx
from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..dependencies.auth import get_current_admin, get_current_user
from ..models.ai_config import (
    ALLOWED_KB_EXTS,
    AiKnowledgeBase,
    AiKnowledgeBaseChunk,
    AiKnowledgeBaseDocument,
    AiKnowledgeBaseSubject,
    AiCustomModel,
    AiCustomModelKnowledgeBaseLink,
    AiFeatureCustomModelBinding,
    AiFeatureSetting,
    AiModelApi,
    AiModelKnowledgeBaseLink,
    AiWorkflowApp,
    StudentCourseAiSelection,
    TeacherKnowledgeBaseDocument,
)
from ..models.user import User
from ..schemas.admin_ai import (
    AiKnowledgeBaseCreate,
    AiKnowledgeBaseOut,
    AiKnowledgeBaseUpdate,
    AiKbDocumentOut,
    AiKbSubjectCreate,
    AiKbSubjectOut,
    AiCustomModelCreate,
    AiCustomModelOut,
    AiCustomModelUpdate,
    AiCustomModelKbDocOut,
    AiFeatureBindingOut,
    AiFeatureBindingUpdate,
    AiCustomerServiceSettingsOut,
    AiCustomerServiceSettingsUpdate,
    AiModelApiCreate,
    AiModelApiOut,
    AiModelApiTestRequest,
    AiModelApiTestResponse,
    AiModelApiUpdate,
    AiModelKbUpdateRequest,
    AiWorkflowAppOut,
    AiWorkflowAppUpdate,
    PublicAiModelOut,
    StudentCourseAiSelectOut,
    StudentCourseAiSelectRequest,
) 
from ..services.ai_workflow import delete_document_chunks, extract_text_from_file, rebuild_document_chunks

router = APIRouter(prefix="/admin/ai", tags=["Admin AI"])

_BASE_UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "uploads", "kb_base")
_TEACHER_UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "uploads", "kb_teacher")
_WORKFLOW_UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "uploads", "kb_workflow")
os.makedirs(_BASE_UPLOAD_DIR, exist_ok=True)
os.makedirs(_TEACHER_UPLOAD_DIR, exist_ok=True)
os.makedirs(_WORKFLOW_UPLOAD_DIR, exist_ok=True)


def _ensure_ext(filename: str) -> str:
    ext = os.path.splitext(filename or "")[1].lower()
    if ext not in ALLOWED_KB_EXTS:
        raise HTTPException(status_code=400, detail=f"不支持的文件格式: {ext}")
    return ext


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", (name or "").strip().lower())
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    return slug or uuid.uuid4().hex[:8]


async def _save_upload(file: UploadFile, upload_dir: str) -> dict:
    ext = _ensure_ext(file.filename)
    stored = f"{uuid.uuid4().hex}{ext}"
    abs_path = os.path.join(upload_dir, stored)

    data = await file.read()
    with open(abs_path, "wb") as f:
        f.write(data)

    rel_url = "/static/uploads/kb_base/" + stored
    if upload_dir.endswith("kb_teacher"):
        rel_url = "/static/uploads/kb_teacher/" + stored
    if upload_dir.endswith("kb_workflow"):
        rel_url = "/static/uploads/kb_workflow/" + stored

    return {
        "stored_filename": stored,
        "file_ext": ext,
        "file_size": len(data),
        "url": rel_url,
        "abs_path": abs_path,
    }


async def _load_kb_or_404(db: AsyncSession, kb_id: int) -> AiKnowledgeBase:
    kb = (await db.execute(select(AiKnowledgeBase).where(AiKnowledgeBase.id == kb_id))).scalars().first()
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")
    return kb


async def _ensure_subject_for_kb(
    db: AsyncSession,
    kb: AiKnowledgeBase,
    label: Optional[str] = None,
) -> AiKnowledgeBaseSubject:
    base_label = (label or f"{kb.name}默认主题").strip()
    unique_name = f"{base_label} (KB {kb.id})"
    stmt = select(AiKnowledgeBaseSubject).where(AiKnowledgeBaseSubject.name == unique_name)
    subject = (await db.execute(stmt)).scalars().first()
    if subject:
        return subject
    subject = AiKnowledgeBaseSubject(name=unique_name, stage=getattr(kb, "feature", None))
    db.add(subject)
    await db.flush()
    return subject


async def _ensure_unique_slug(db: AsyncSession, slug: str) -> str:
    slug = _slugify(slug)
    base = slug
    idx = 1
    while True:
        existed = (
            await db.execute(select(AiKnowledgeBase).where(AiKnowledgeBase.slug == slug))
        ).scalars().first()
        if not existed:
            return slug
        slug = f"{base}-{idx}"
        idx += 1


async def _collect_kb_stats(db: AsyncSession, kb_ids: List[int]) -> dict[int, dict]:
    stats: dict[int, dict] = {}
    if not kb_ids:
        return stats
    doc_stmt = (
        select(AiKnowledgeBaseDocument.knowledge_base_id, func.count())
        .where(AiKnowledgeBaseDocument.knowledge_base_id.in_(kb_ids))
        .group_by(AiKnowledgeBaseDocument.knowledge_base_id)
    )
    chunk_stmt = (
        select(AiKnowledgeBaseChunk.knowledge_base_id, func.count())
        .where(AiKnowledgeBaseChunk.knowledge_base_id.in_(kb_ids))
        .group_by(AiKnowledgeBaseChunk.knowledge_base_id)
    )
    for kb_id, count in (await db.execute(doc_stmt)).all():
        stats[int(kb_id)] = {"documents": int(count), "chunks": 0}
    for kb_id, count in (await db.execute(chunk_stmt)).all():
        stats.setdefault(int(kb_id), {"documents": 0, "chunks": 0})["chunks"] = int(count)
    return stats


def _kb_to_out(kb: AiKnowledgeBase, stats: dict[int, dict]) -> AiKnowledgeBaseOut:
    kb_stats = stats.get(int(kb.id), {})
    return AiKnowledgeBaseOut(
        id=kb.id,
        slug=kb.slug,
        name=kb.name,
        description=kb.description,
        owner_type=kb.owner_type,
        owner_user_id=kb.owner_user_id,
        course_id=kb.course_id,
        feature=kb.feature,
        is_default=kb.is_default,
        document_count=kb_stats.get("documents", 0),
        chunk_count=kb_stats.get("chunks", 0),
        created_at=kb.created_at,
        updated_at=kb.updated_at,
    )


def _load_json_settings(settings_json: str | None) -> dict:
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


async def _collect_doc_chunk_counts(db: AsyncSession, doc_ids: List[int]) -> dict[int, int]:
    if not doc_ids:
        return {}
    stmt = (
        select(AiKnowledgeBaseChunk.document_id, func.count())
        .where(AiKnowledgeBaseChunk.document_id.in_(doc_ids))
        .group_by(AiKnowledgeBaseChunk.document_id)
    )
    return {int(doc_id): int(count) for doc_id, count in (await db.execute(stmt)).all()}


@router.get("/model-apis", response_model=List[AiModelApiOut])
async def list_model_apis(db: AsyncSession = Depends(get_db), _: User = Depends(get_current_admin)):
    res = await db.execute(select(AiModelApi).order_by(AiModelApi.id.desc()))
    return [
        AiModelApiOut(
            id=o.id,
            name=o.name,
            provider=o.provider,
            model_name=o.model_name,
            endpoint=o.endpoint,
            timeout_seconds=o.timeout_seconds,
            quota_per_hour=o.quota_per_hour,
            enabled=o.enabled,
            is_default=o.is_default,
            created_at=o.created_at,
            updated_at=o.updated_at,
        )
        for o in res.scalars().all()
    ]


@router.post("/model-apis", response_model=AiModelApiOut)
async def create_model_api(payload: AiModelApiCreate, db: AsyncSession = Depends(get_db), admin: User = Depends(get_current_admin)):
    obj = AiModelApi(
        name=payload.name,
        provider=payload.provider,
        model_name=payload.model_name,
        endpoint=payload.endpoint,
        api_key=payload.api_key,
        timeout_seconds=payload.timeout_seconds,
        quota_per_hour=payload.quota_per_hour,
        enabled=payload.enabled,
        is_default=payload.is_default,
    )
    db.add(obj)
    await db.flush()

    if payload.is_default:
        await db.execute(update(AiModelApi).where(AiModelApi.id != obj.id).values(is_default=False))

    await db.commit()
    await db.refresh(obj)
    return AiModelApiOut(
        id=obj.id,
        name=obj.name,
        provider=obj.provider,
        model_name=obj.model_name,
        endpoint=obj.endpoint,
        timeout_seconds=obj.timeout_seconds,
        quota_per_hour=obj.quota_per_hour,
        enabled=obj.enabled,
        is_default=obj.is_default,
        created_at=obj.created_at,
        updated_at=obj.updated_at,
    )


@router.put("/model-apis/{api_id}", response_model=AiModelApiOut)
async def update_model_api(api_id: int, payload: AiModelApiUpdate, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_admin)):
    obj = (await db.execute(select(AiModelApi).where(AiModelApi.id == api_id))).scalars().first()
    if not obj:
        raise HTTPException(status_code=404, detail="模型 API 不存在")

    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)

    if payload.is_default is True:
        await db.execute(update(AiModelApi).where(AiModelApi.id != obj.id).values(is_default=False))

    await db.commit()
    await db.refresh(obj)
    return AiModelApiOut(
        id=obj.id,
        name=obj.name,
        provider=obj.provider,
        model_name=obj.model_name,
        endpoint=obj.endpoint,
        timeout_seconds=obj.timeout_seconds,
        quota_per_hour=obj.quota_per_hour,
        enabled=obj.enabled,
        is_default=obj.is_default,
        created_at=obj.created_at,
        updated_at=obj.updated_at,
    )


@router.delete("/model-apis/{api_id}")
async def delete_model_api(api_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_admin)):
    obj = (await db.execute(select(AiModelApi).where(AiModelApi.id == api_id))).scalars().first()
    if not obj:
        return {"ok": True}

    await db.delete(obj)
    await db.commit()
    return {"ok": True}


@router.post("/model-apis/test", response_model=AiModelApiTestResponse)
async def test_model_api(
    payload: AiModelApiTestRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    provider = (payload.provider or "").strip()
    endpoint = (payload.endpoint or "").strip().rstrip("/")
    api_key = (payload.api_key or "").strip()
    model_name = (payload.model_name or "").strip()
    prompt = (payload.prompt or "ping").strip() or "ping"

    # 若携带 api_id，则补全缺失字段（便于前端仅传 ID 与 prompt）
    if payload.api_id and (not provider or not endpoint or not model_name or not api_key):
        obj = (await db.execute(select(AiModelApi).where(AiModelApi.id == payload.api_id))).scalars().first()
        if obj:
            provider = provider or obj.provider or ""
            endpoint = endpoint or obj.endpoint or ""
            api_key = api_key or obj.api_key or ""
            model_name = model_name or obj.model_name or ""

    if not endpoint or not api_key or not model_name or not provider:
        raise HTTPException(status_code=400, detail="endpoint / api_key / model_name / provider 不能为空")

    try:
        timeout = httpx.Timeout(payload.timeout_seconds)
        async with httpx.AsyncClient(timeout=timeout) as client:
            if provider == "dashscope_openai":
                headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
                resp = await client.post(
                    f"{endpoint}/chat/completions",
                    json={
                        "model": model_name,
                        "messages": [{"role": "user", "content": prompt}],
                        "stream": False,
                    },
                    headers=headers,
                )
            elif provider == "ark_responses":
                headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
                resp = await client.post(
                    f"{endpoint}/responses",
                    json={
                        "model": model_name,
                        "stream": False,
                        "input": [{"role": "user", "content": [{"type": "input_text", "text": prompt}]}],
                    },
                    headers=headers,
                )
            else:
                return AiModelApiTestResponse(ok=False, message="不支持的 provider（仅 dashscope_openai / ark_responses）")

        if resp.status_code < 200 or resp.status_code >= 300:
            return AiModelApiTestResponse(ok=False, message=f"连接失败: HTTP {resp.status_code} {resp.text[:200]}")

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

        return AiModelApiTestResponse(
            ok=True,
            message="连接成功",
            output=(output_text or resp.text or "").strip()[:800],
        )
    except Exception as e:
        return AiModelApiTestResponse(ok=False, message=f"连接异常: {e}")


@router.get("/kb/subjects", response_model=List[AiKbSubjectOut])
async def list_kb_subjects(db: AsyncSession = Depends(get_db), _: User = Depends(get_current_admin)):
    res = await db.execute(select(AiKnowledgeBaseSubject).order_by(AiKnowledgeBaseSubject.id.desc()))
    return [
        AiKbSubjectOut(id=s.id, name=s.name, stage=getattr(s, "stage", None), enabled=getattr(s, "enabled", True), created_at=s.created_at)
        for s in res.scalars().all()
    ]


@router.post("/kb/subjects", response_model=AiKbSubjectOut)
async def create_kb_subject(payload: AiKbSubjectCreate, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_admin)):
    name = (payload.name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="学科名称不能为空")

    exists = (await db.execute(select(AiKnowledgeBaseSubject).where(AiKnowledgeBaseSubject.name == name))).scalars().first()
    if exists:
        return AiKbSubjectOut(id=exists.id, name=exists.name, stage=getattr(exists, "stage", None), enabled=getattr(exists, "enabled", True), created_at=exists.created_at)

    obj = AiKnowledgeBaseSubject(name=name, stage=(payload.stage or None))
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return AiKbSubjectOut(id=obj.id, name=obj.name, stage=getattr(obj, "stage", None), enabled=getattr(obj, "enabled", True), created_at=obj.created_at)


@router.get("/kb/documents", response_model=List[AiKbDocumentOut])
async def list_kb_documents(subject_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_admin)):
    res = await db.execute(
        select(AiKnowledgeBaseDocument)
        .where(AiKnowledgeBaseDocument.subject_id == subject_id)
        .order_by(AiKnowledgeBaseDocument.id.desc())
    )
    return [
        AiKbDocumentOut(
            id=d.id,
            subject_id=d.subject_id,
            title=d.title,
            original_filename=d.original_filename,
            url=d.url,
            file_ext=d.file_ext,
            file_size=d.file_size,
            enabled=getattr(d, "enabled", True),
            created_at=d.created_at,
            updated_at=getattr(d, "updated_at", None),
        )
        for d in res.scalars().all()
    ]


@router.post("/kb/upload", response_model=AiKbDocumentOut)
async def upload_kb_document(
    subject_id: int = Form(...),
    title: str = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    subj = (await db.execute(select(AiKnowledgeBaseSubject).where(AiKnowledgeBaseSubject.id == subject_id))).scalars().first()
    if not subj:
        raise HTTPException(status_code=404, detail="学科不存在")

    meta = await _save_upload(file, _BASE_UPLOAD_DIR)
    obj = AiKnowledgeBaseDocument(
        subject_id=subject_id,
        title=(title or file.filename or "").strip() or "未命名文档",
        original_filename=file.filename or meta["stored_filename"],
        stored_filename=meta["stored_filename"],
        url=meta["url"],
        file_ext=meta["file_ext"],
        file_size=meta["file_size"],
        uploaded_by_admin=str(getattr(admin, "username", "")),
        enabled=True,
    )
    db.add(obj)
    await db.commit()
    await db.refresh(obj)

    return AiKbDocumentOut(
        id=obj.id,
        subject_id=obj.subject_id,
        title=obj.title,
        original_filename=obj.original_filename,
        url=obj.url,
        file_ext=obj.file_ext,
        file_size=obj.file_size,
        enabled=getattr(obj, "enabled", True),
        created_at=obj.created_at,
        updated_at=getattr(obj, "updated_at", None),
    )


@router.delete("/kb/documents/{doc_id}")
async def delete_kb_document(doc_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_admin)):
    doc = (await db.execute(select(AiKnowledgeBaseDocument).where(AiKnowledgeBaseDocument.id == doc_id))).scalars().first()
    if not doc:
        return {"ok": True}

    # best-effort delete file
    try:
        abs_path = os.path.join(_BASE_UPLOAD_DIR, doc.stored_filename)
        if os.path.isfile(abs_path):
            os.remove(abs_path)
    except Exception:
        pass

    await db.delete(doc)
    await db.commit()
    return {"ok": True}


@router.put("/model-apis/{api_id}/kb")
async def update_model_kb_links(api_id: int, payload: AiModelKbUpdateRequest, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_admin)):
    model = (await db.execute(select(AiModelApi).where(AiModelApi.id == api_id))).scalars().first()
    if not model:
        raise HTTPException(status_code=404, detail="模型 API 不存在")

    ids = list(dict.fromkeys([int(x) for x in payload.kb_document_ids if int(x) > 0]))

    # remove old
    await db.execute(
        delete(AiModelKnowledgeBaseLink)
        .where(AiModelKnowledgeBaseLink.model_api_id == api_id)
        .where(~AiModelKnowledgeBaseLink.kb_document_id.in_(ids) if ids else True)
    )

    if ids:
        existing = await db.execute(
            select(AiModelKnowledgeBaseLink.kb_document_id)
            .where(AiModelKnowledgeBaseLink.model_api_id == api_id)
        )
        have = set(int(x) for x in existing.scalars().all())
        for idx, doc_id in enumerate(ids):
            if int(doc_id) not in have:
                # ensure doc exists
                ok = (await db.execute(select(AiKnowledgeBaseDocument.id).where(AiKnowledgeBaseDocument.id == doc_id))).scalars().first()
                if ok:
                    db.add(AiModelKnowledgeBaseLink(model_api_id=api_id, kb_document_id=int(doc_id), priority=int(idx)))

        # sync priorities for all links
        for idx, doc_id in enumerate(ids):
            await db.execute(
                update(AiModelKnowledgeBaseLink)
                .where(
                    AiModelKnowledgeBaseLink.model_api_id == api_id,
                    AiModelKnowledgeBaseLink.kb_document_id == int(doc_id),
                )
                .values(priority=int(idx))
            )

    await db.commit()
    return {"ok": True, "kb_document_ids": ids}


# ----------------- AI Workflow Knowledge Bases -----------------

@router.get("/workflows/knowledge-bases", response_model=List[AiKnowledgeBaseOut])
async def list_workflow_knowledge_bases(
    feature: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    stmt = select(AiKnowledgeBase).order_by(AiKnowledgeBase.created_at.desc())
    if feature:
        stmt = stmt.where(AiKnowledgeBase.feature == feature)
    res = await db.execute(stmt)
    kbs = res.scalars().all()
    stats = await _collect_kb_stats(db, [kb.id for kb in kbs])
    return [_kb_to_out(kb, stats) for kb in kbs]


@router.post("/workflows/knowledge-bases", response_model=AiKnowledgeBaseOut)
async def create_workflow_knowledge_base(
    payload: AiKnowledgeBaseCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    name = (payload.name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="知识库名称不能为空")
    slug_input = payload.slug or name
    slug = await _ensure_unique_slug(db, slug_input)
    kb = AiKnowledgeBase(
        slug=slug,
        name=name,
        description=(payload.description or "").strip() or None,
        feature=(payload.feature or "").strip() or None,
        owner_type="system",
        is_default=bool(payload.is_default),
    )
    db.add(kb)
    await db.flush()
    if kb.is_default and kb.feature:
        await db.execute(
            update(AiKnowledgeBase)
            .where(AiKnowledgeBase.feature == kb.feature, AiKnowledgeBase.id != kb.id)
            .values(is_default=False)
        )
    await db.commit()
    await db.refresh(kb)
    stats = await _collect_kb_stats(db, [kb.id])
    return _kb_to_out(kb, stats)


@router.put("/workflows/knowledge-bases/{kb_id}", response_model=AiKnowledgeBaseOut)
async def update_workflow_knowledge_base(
    kb_id: int,
    payload: AiKnowledgeBaseUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    kb = await _load_kb_or_404(db, kb_id)
    data = payload.model_dump(exclude_unset=True)
    if "name" in data:
        kb.name = (data["name"] or "").strip() or kb.name
    if "description" in data:
        kb.description = (data["description"] or "").strip() or None
    if "feature" in data:
        kb.feature = (data["feature"] or "").strip() or None
    if "is_default" in data and data["is_default"] is not None:
        kb.is_default = bool(data["is_default"])
        if kb.is_default and kb.feature:
            await db.execute(
                update(AiKnowledgeBase)
                .where(AiKnowledgeBase.feature == kb.feature, AiKnowledgeBase.id != kb.id)
                .values(is_default=False)
            )
    await db.commit()
    await db.refresh(kb)
    stats = await _collect_kb_stats(db, [kb.id])
    return _kb_to_out(kb, stats)


@router.delete("/workflows/knowledge-bases/{kb_id}")
async def delete_workflow_knowledge_base(
    kb_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    kb = await _load_kb_or_404(db, kb_id)
    in_use = (
        await db.execute(select(AiWorkflowApp.id).where(AiWorkflowApp.knowledge_base_id == kb.id))
    ).scalars().first()
    if in_use:
        raise HTTPException(status_code=400, detail="知识库已绑定 AI 工作流，无法删除")
    await db.delete(kb)
    await db.commit()
    return {"ok": True}


@router.get("/workflows/knowledge-bases/{kb_id}/documents", response_model=List[AiKbDocumentOut])
async def list_workflow_documents(
    kb_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    await _load_kb_or_404(db, kb_id)
    stmt = (
        select(AiKnowledgeBaseDocument)
        .where(AiKnowledgeBaseDocument.knowledge_base_id == kb_id)
        .order_by(AiKnowledgeBaseDocument.created_at.desc())
    )
    res = await db.execute(stmt)
    docs = res.scalars().all()
    chunk_counts = await _collect_doc_chunk_counts(db, [doc.id for doc in docs])
    out: List[AiKbDocumentOut] = []
    for doc in docs:
        out.append(
            AiKbDocumentOut(
                id=doc.id,
                subject_id=doc.subject_id or 0,
                knowledge_base_id=doc.knowledge_base_id,
                title=doc.title,
                original_filename=doc.original_filename,
                url=doc.url,
                file_ext=doc.file_ext,
                file_size=doc.file_size,
                enabled=getattr(doc, "enabled", True),
                created_at=doc.created_at,
                updated_at=doc.updated_at,
                chunk_count=chunk_counts.get(doc.id, 0),
            )
        )
    return out


@router.post("/workflows/knowledge-bases/{kb_id}/documents/upload", response_model=AiKbDocumentOut)
async def upload_workflow_document(
    kb_id: int,
    title: str = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    kb = await _load_kb_or_404(db, kb_id)
    subject = await _ensure_subject_for_kb(db, kb)
    meta = await _save_upload(file, _WORKFLOW_UPLOAD_DIR)
    doc = AiKnowledgeBaseDocument(
        knowledge_base_id=kb.id,
        subject_id=subject.id,
        title=(title or file.filename or "").strip() or "未命名文档",
        original_filename=file.filename or meta["stored_filename"],
        stored_filename=meta["stored_filename"],
        url=meta["url"],
        file_ext=meta["file_ext"],
        file_size=meta["file_size"],
        uploaded_by_admin=str(getattr(admin, "username", "")),
        enabled=True,
    )
    db.add(doc)
    await db.flush()
    text = extract_text_from_file(meta["abs_path"], meta["file_ext"])
    chunk_count = await rebuild_document_chunks(db, doc, text)
    await db.commit()
    await db.refresh(doc)
    return AiKbDocumentOut(
        id=doc.id,
        subject_id=doc.subject_id or 0,
        knowledge_base_id=kb.id,
        title=doc.title,
        original_filename=doc.original_filename,
        url=doc.url,
        file_ext=doc.file_ext,
        file_size=doc.file_size,
        enabled=True,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
        chunk_count=chunk_count,
    )


@router.post("/workflows/knowledge-bases/{kb_id}/documents/manual", response_model=AiKbDocumentOut)
async def create_manual_workflow_document(
    kb_id: int,
    payload: dict = Body(...),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    kb = await _load_kb_or_404(db, kb_id)
    title = (payload.get("title") or "").strip() or "手动录入文档"
    content = (payload.get("content") or "").strip()
    if not content:
        raise HTTPException(status_code=400, detail="内容不能为空")
    subject = await _ensure_subject_for_kb(db, kb)
    doc = AiKnowledgeBaseDocument(
        knowledge_base_id=kb.id,
        subject_id=subject.id,
        title=title,
        original_filename=f"{uuid.uuid4().hex}.txt",
        stored_filename="",
        url="",
        file_ext=".txt",
        file_size=len(content.encode("utf-8")),
        uploaded_by_admin=str(getattr(admin, "username", "")),
        enabled=True,
    )
    db.add(doc)
    await db.flush()
    chunk_count = await rebuild_document_chunks(db, doc, content)
    await db.commit()
    await db.refresh(doc)
    return AiKbDocumentOut(
        id=doc.id,
        subject_id=doc.subject_id or 0,
        knowledge_base_id=kb.id,
        title=doc.title,
        original_filename=doc.original_filename,
        url=doc.url,
        file_ext=doc.file_ext,
        file_size=doc.file_size,
        enabled=True,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
        chunk_count=chunk_count,
    )


@router.delete("/workflows/documents/{doc_id}")
async def delete_workflow_document(
    doc_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    doc = (
        await db.execute(select(AiKnowledgeBaseDocument).where(AiKnowledgeBaseDocument.id == doc_id))
    ).scalars().first()
    if not doc:
        return {"ok": True}
    if not doc.knowledge_base_id:
        raise HTTPException(status_code=400, detail="该文档未绑定 AI 工作流知识库")
    await delete_document_chunks(db, doc.id)
    stored = (doc.stored_filename or "").strip()
    if stored:
        for folder in (_WORKFLOW_UPLOAD_DIR, _BASE_UPLOAD_DIR, _TEACHER_UPLOAD_DIR):
            try:
                abs_path = os.path.join(folder, stored)
                if os.path.isfile(abs_path):
                    os.remove(abs_path)
                    break
            except Exception:
                pass
    await db.delete(doc)
    await db.commit()
    return {"ok": True}


# ----------------- AI Workflow Apps -----------------

@router.get("/workflows/apps", response_model=List[AiWorkflowAppOut])
async def list_workflow_apps(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    res = await db.execute(
        select(AiWorkflowApp).order_by(AiWorkflowApp.updated_at.desc().nullslast(), AiWorkflowApp.id.desc())
    )
    items = res.scalars().all()
    out: List[AiWorkflowAppOut] = []
    for app in items:
        out.append(
            AiWorkflowAppOut(
                code=app.code,
                type=app.type,
                name=app.name,
                status=app.status,
                knowledge_base_id=app.knowledge_base_id,
                model_api_id=app.model_api_id,
                owner_user_id=app.owner_user_id,
                course_id=app.course_id,
                settings=_load_json_settings(app.settings_json),
                updated_at=app.updated_at,
            )
        )
    return out


@router.post("/workflows/apps", response_model=AiWorkflowAppOut)
async def create_workflow_app(
    payload: AiWorkflowAppCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    code = (payload.code or "").strip()
    if not code:
        raise HTTPException(status_code=400, detail="code 不能为空")
    existed = (await db.execute(select(AiWorkflowApp).where(AiWorkflowApp.code == code))).scalars().first()
    if existed:
        raise HTTPException(status_code=400, detail="code 已存在")
    app = AiWorkflowApp(
        code=code,
        type=(payload.type or "").strip() or "customer_service",
        name=(payload.name or "").strip() or code,
        status=payload.status or "enabled",
        knowledge_base_id=payload.knowledge_base_id,
        model_api_id=payload.model_api_id,
        owner_user_id=payload.owner_user_id,
        course_id=payload.course_id,
        settings_json=json.dumps(payload.settings or {}, ensure_ascii=False) if payload.settings is not None else None,
    )
    db.add(app)
    await db.commit()
    await db.refresh(app)
    return AiWorkflowAppOut(
        code=app.code,
        type=app.type,
        name=app.name,
        status=app.status,
        knowledge_base_id=app.knowledge_base_id,
        model_api_id=app.model_api_id,
        owner_user_id=app.owner_user_id,
        course_id=app.course_id,
        settings=_load_json_settings(app.settings_json),
        updated_at=app.updated_at,
    )


@router.put("/workflows/apps/{code}", response_model=AiWorkflowAppOut)
async def update_workflow_app(
    code: str,
    payload: AiWorkflowAppUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    app = (await db.execute(select(AiWorkflowApp).where(AiWorkflowApp.code == code))).scalars().first()
    if not app:
        raise HTTPException(status_code=404, detail="工作流不存在")
    data = payload.model_dump(exclude_unset=True)
    if "name" in data and data["name"]:
        app.name = data["name"].strip()
    if "knowledge_base_id" in data:
        if data["knowledge_base_id"]:
            await _load_kb_or_404(db, int(data["knowledge_base_id"]))
            app.knowledge_base_id = int(data["knowledge_base_id"])
        else:
            app.knowledge_base_id = None
    if "model_api_id" in data:
        if data["model_api_id"]:
            model = (
                await db.execute(select(AiModelApi).where(AiModelApi.id == int(data["model_api_id"])))
            ).scalars().first()
            if not model or not model.enabled:
                raise HTTPException(status_code=404, detail="模型不存在或未启用")
            app.model_api_id = int(data["model_api_id"])
        else:
            app.model_api_id = None
    if "status" in data and data["status"]:
        app.status = data["status"]
    if "settings" in data and data["settings"] is not None:
        try:
            app.settings_json = json.dumps(data["settings"], ensure_ascii=False)
        except Exception:
            raise HTTPException(status_code=400, detail="settings 格式错误")
    await db.commit()
    await db.refresh(app)
    return AiWorkflowAppOut(
        code=app.code,
        type=app.type,
        name=app.name,
        status=app.status,
        knowledge_base_id=app.knowledge_base_id,
        model_api_id=app.model_api_id,
        owner_user_id=app.owner_user_id,
        course_id=app.course_id,
        settings=_load_json_settings(app.settings_json),
        updated_at=app.updated_at,
    )


@router.delete("/workflows/apps/{code}")
async def delete_workflow_app(
    code: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    app = (await db.execute(select(AiWorkflowApp).where(AiWorkflowApp.code == code))).scalars().first()
    if not app:
        return {"ok": True}
    await db.delete(app)
    await db.commit()
    return {"ok": True}


# ----------------- Custom Models (Dify-like) -----------------
# ----------------- Custom Models (Dify-like) -----------------

def _validate_feature(feature: str) -> str:
    feature = (feature or "").strip()
    if feature not in {"customer_service", "lesson_plan", "course_assistant"}:
        raise HTTPException(status_code=400, detail="不支持的 feature")
    return feature


@router.get("/custom-models", response_model=List[AiCustomModelOut])
async def list_custom_models(db: AsyncSession = Depends(get_db), _: User = Depends(get_current_admin)):
    res = await db.execute(select(AiCustomModel).order_by(AiCustomModel.updated_at.desc(), AiCustomModel.id.desc()))
    items = res.scalars().all()
    if not items:
        return []

    ids = [x.id for x in items]
    base_ids = list({x.base_model_api_id for x in items})
    subj_ids = list({x.primary_subject_id for x in items if x.primary_subject_id})

    base_res = await db.execute(select(AiModelApi.id, AiModelApi.name).where(AiModelApi.id.in_(base_ids)))
    base_map = {i: n for i, n in base_res.all()}

    subj_map: dict[int, str] = {}
    if subj_ids:
        subj_res = await db.execute(select(AiKnowledgeBaseSubject.id, AiKnowledgeBaseSubject.name).where(AiKnowledgeBaseSubject.id.in_(subj_ids)))
        subj_map = {i: n for i, n in subj_res.all()}

    link_res = await db.execute(
        select(
            AiCustomModelKnowledgeBaseLink.custom_model_id,
            AiCustomModelKnowledgeBaseLink.priority,
            AiKnowledgeBaseDocument.id,
            AiKnowledgeBaseDocument.title,
            AiKnowledgeBaseDocument.subject_id,
            AiKnowledgeBaseSubject.name,
        )
        .join(AiKnowledgeBaseDocument, AiKnowledgeBaseDocument.id == AiCustomModelKnowledgeBaseLink.kb_document_id)
        .join(AiKnowledgeBaseSubject, AiKnowledgeBaseSubject.id == AiKnowledgeBaseDocument.subject_id)
        .where(AiCustomModelKnowledgeBaseLink.custom_model_id.in_(ids))
        .order_by(AiCustomModelKnowledgeBaseLink.custom_model_id.asc(), AiCustomModelKnowledgeBaseLink.priority.asc(), AiCustomModelKnowledgeBaseLink.id.asc())
    )
    kb_group: dict[int, list[AiCustomModelKbDocOut]] = {}
    for cm_id, _prio, doc_id, title, subject_id, subject_name in link_res.all():
        kb_group.setdefault(int(cm_id), []).append(
            AiCustomModelKbDocOut(id=int(doc_id), title=title, subject_id=int(subject_id), subject_name=subject_name)
        )

    out: list[AiCustomModelOut] = []
    for x in items:
        out.append(
            AiCustomModelOut(
                id=x.id,
                name=x.name,
                remark=getattr(x, "remark", None),
                enabled=x.enabled,
                base_model_api_id=x.base_model_api_id,
                base_model_name=base_map.get(x.base_model_api_id),
                primary_subject_id=x.primary_subject_id,
                primary_subject_name=subj_map.get(x.primary_subject_id) if x.primary_subject_id else None,
                kb_documents=kb_group.get(x.id, []),
                created_at=x.created_at,
                updated_at=x.updated_at,
            )
        )
    return out


@router.post("/custom-models", response_model=AiCustomModelOut)
async def create_custom_model(payload: AiCustomModelCreate, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_admin)):
    name = (payload.name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="name 不能为空")
    if not payload.base_model_api_id:
        raise HTTPException(status_code=400, detail="base_model_api_id 不能为空")

    base = (await db.execute(select(AiModelApi).where(AiModelApi.id == payload.base_model_api_id))).scalars().first()
    if not base:
        raise HTTPException(status_code=404, detail="底座模型不存在")

    kb_ids = list(dict.fromkeys([int(x) for x in (payload.kb_document_ids or []) if int(x) > 0]))
    if not kb_ids:
        raise HTTPException(status_code=400, detail="至少选择 1 个知识库")

    # ensure docs exist
    docs = await db.execute(select(AiKnowledgeBaseDocument.id).where(AiKnowledgeBaseDocument.id.in_(kb_ids)))
    have = set(int(x) for x in docs.scalars().all())
    missing = [x for x in kb_ids if x not in have]
    if missing:
        raise HTTPException(status_code=404, detail=f"知识库不存在: {missing[:5]}")

    if payload.primary_subject_id:
        subj_ok = (
            await db.execute(select(AiKnowledgeBaseSubject.id).where(AiKnowledgeBaseSubject.id == int(payload.primary_subject_id)))
        ).scalars().first()
        if not subj_ok:
            raise HTTPException(status_code=404, detail="primary_subject_id 对应学科不存在")

    obj = AiCustomModel(
        name=name,
        remark=(payload.remark or "").strip() or None,
        enabled=bool(payload.enabled),
        base_model_api_id=int(payload.base_model_api_id),
        primary_subject_id=int(payload.primary_subject_id) if payload.primary_subject_id else None,
    )
    db.add(obj)
    await db.flush()

    for idx, doc_id in enumerate(kb_ids):
        db.add(AiCustomModelKnowledgeBaseLink(custom_model_id=obj.id, kb_document_id=int(doc_id), priority=idx))

    await db.commit()
    items = await list_custom_models(db, _)
    for it in items:
        if it.id == int(obj.id):
            return it
    raise HTTPException(status_code=500, detail="Failed to load created custom model")


@router.put("/custom-models/{custom_id}", response_model=AiCustomModelOut)
async def update_custom_model(custom_id: int, payload: AiCustomModelUpdate, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_admin)):
    obj = (await db.execute(select(AiCustomModel).where(AiCustomModel.id == custom_id))).scalars().first()
    if not obj:
        raise HTTPException(status_code=404, detail="定制模型不存在")

    data = payload.model_dump(exclude_unset=True)
    if "name" in data:
        nm = (data["name"] or "").strip()
        if not nm:
            raise HTTPException(status_code=400, detail="name 不能为空")
        obj.name = nm
    if "remark" in data:
        obj.remark = (data["remark"] or "").strip() or None
    if "enabled" in data:
        obj.enabled = bool(data["enabled"])
    if "base_model_api_id" in data and data["base_model_api_id"]:
        base = (await db.execute(select(AiModelApi.id).where(AiModelApi.id == int(data["base_model_api_id"]))))
        if not base.scalars().first():
            raise HTTPException(status_code=404, detail="底座模型不存在")
        obj.base_model_api_id = int(data["base_model_api_id"])
    if "primary_subject_id" in data:
        if data["primary_subject_id"]:
            subj_ok = (
                await db.execute(
                    select(AiKnowledgeBaseSubject.id).where(AiKnowledgeBaseSubject.id == int(data["primary_subject_id"]))
                )
            ).scalars().first()
            if not subj_ok:
                raise HTTPException(status_code=404, detail="primary_subject_id 对应学科不存在")
        obj.primary_subject_id = int(data["primary_subject_id"]) if data["primary_subject_id"] else None

    if "kb_document_ids" in data and data["kb_document_ids"] is not None:
        kb_ids = list(dict.fromkeys([int(x) for x in (data["kb_document_ids"] or []) if int(x) > 0]))
        if not kb_ids:
            raise HTTPException(status_code=400, detail="至少选择 1 个知识库")
        docs = await db.execute(select(AiKnowledgeBaseDocument.id).where(AiKnowledgeBaseDocument.id.in_(kb_ids)))
        have = set(int(x) for x in docs.scalars().all())
        missing = [x for x in kb_ids if x not in have]
        if missing:
            raise HTTPException(status_code=404, detail=f"知识库不存在: {missing[:5]}")

        await db.execute(delete(AiCustomModelKnowledgeBaseLink).where(AiCustomModelKnowledgeBaseLink.custom_model_id == custom_id))
        for idx, doc_id in enumerate(kb_ids):
            db.add(AiCustomModelKnowledgeBaseLink(custom_model_id=custom_id, kb_document_id=int(doc_id), priority=idx))

    await db.commit()
    # return rebuilt output
    all_items = await list_custom_models(db, _)
    for it in all_items:
        if it.id == custom_id:
            return it
    raise HTTPException(status_code=500, detail="Failed to load updated custom model")


@router.delete("/custom-models/{custom_id}")
async def delete_custom_model(custom_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_admin)):
    obj = (await db.execute(select(AiCustomModel).where(AiCustomModel.id == custom_id))).scalars().first()
    if not obj:
        return {"ok": True}

    await db.execute(delete(AiFeatureCustomModelBinding).where(AiFeatureCustomModelBinding.custom_model_id == int(custom_id)))
    await db.execute(delete(AiCustomModelKnowledgeBaseLink).where(AiCustomModelKnowledgeBaseLink.custom_model_id == int(custom_id)))
    await db.delete(obj)
    await db.commit()
    return {"ok": True}


# ----------------- AI Feature bindings -----------------

@router.get("/feature-bindings/{feature}", response_model=AiFeatureBindingOut)
async def get_feature_bindings(feature: str, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_admin)):
    feature = _validate_feature(feature)
    res = await db.execute(
        select(AiFeatureCustomModelBinding.custom_model_id)
        .where(AiFeatureCustomModelBinding.feature == feature)
        .order_by(AiFeatureCustomModelBinding.sort_order.asc(), AiFeatureCustomModelBinding.id.asc())
    )
    ids = [int(x) for x in res.scalars().all()]
    return AiFeatureBindingOut(feature=feature, custom_model_ids=ids)


@router.put("/feature-bindings/{feature}", response_model=AiFeatureBindingOut)
async def save_feature_bindings(feature: str, payload: AiFeatureBindingUpdate, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_admin)):
    feature = _validate_feature(feature)
    ids = list(dict.fromkeys([int(x) for x in (payload.custom_model_ids or []) if int(x) > 0]))

    if ids:
        ok_res = await db.execute(select(AiCustomModel.id).where(AiCustomModel.id.in_(ids)))
        have = set(int(x) for x in ok_res.scalars().all())
        missing = [x for x in ids if x not in have]
        if missing:
            raise HTTPException(status_code=404, detail=f"定制模型不存在: {missing[:5]}")

    await db.execute(delete(AiFeatureCustomModelBinding).where(AiFeatureCustomModelBinding.feature == feature))
    for idx, cid in enumerate(ids):
        db.add(AiFeatureCustomModelBinding(feature=feature, custom_model_id=int(cid), sort_order=idx))
    await db.commit()
    return AiFeatureBindingOut(feature=feature, custom_model_ids=ids)


# ----------------- AI Customer Service settings -----------------

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


async def _get_or_create_feature_setting(db: AsyncSession, feature: str) -> AiFeatureSetting:
    obj = (await db.execute(select(AiFeatureSetting).where(AiFeatureSetting.feature == feature))).scalars().first()
    if obj:
        return obj
    obj = AiFeatureSetting(feature=feature, settings_json=json.dumps(_customer_service_default_settings(), ensure_ascii=False))
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.get("/customer-service/settings", response_model=AiCustomerServiceSettingsOut)
async def get_customer_service_settings(db: AsyncSession = Depends(get_db), _: User = Depends(get_current_admin)):
    obj = await _get_or_create_feature_setting(db, "customer_service")
    try:
        data = json.loads(obj.settings_json or "{}")
    except Exception:
        data = {}
    data = _normalize_customer_service_settings(data)
    return AiCustomerServiceSettingsOut(**data)


@router.put("/customer-service/settings", response_model=AiCustomerServiceSettingsOut)
async def update_customer_service_settings(
    payload: AiCustomerServiceSettingsUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    obj = await _get_or_create_feature_setting(db, "customer_service")
    try:
        current = json.loads(obj.settings_json or "{}")
    except Exception:
        current = {}

    patch = payload.model_dump(exclude_unset=True)
    merged = _normalize_customer_service_settings({**current, **patch})
    obj.settings_json = json.dumps(merged, ensure_ascii=False)
    await db.commit()
    return AiCustomerServiceSettingsOut(**merged)


# ----------------- Teacher / Student sync endpoints (minimal) -----------------

@router.get("/public/models", response_model=List[PublicAiModelOut], include_in_schema=False)
async def list_public_models(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    # enabled models only
    res = await db.execute(select(AiModelApi).where(AiModelApi.enabled == True).order_by(AiModelApi.is_default.desc(), AiModelApi.id.desc()))
    models = res.scalars().all()
    if not models:
        return []

    model_ids = [m.id for m in models]
    link_res = await db.execute(
        select(AiModelKnowledgeBaseLink.model_api_id, AiKnowledgeBaseSubject.name)
        .join(AiKnowledgeBaseDocument, AiKnowledgeBaseDocument.id == AiModelKnowledgeBaseLink.kb_document_id)
        .join(AiKnowledgeBaseSubject, AiKnowledgeBaseSubject.id == AiKnowledgeBaseDocument.subject_id)
        .where(AiModelKnowledgeBaseLink.model_api_id.in_(model_ids))
    )
    subj_map: dict[int, set[str]] = {}
    for mid, sname in link_res.all():
        subj_map.setdefault(mid, set()).add(sname)

    return [
        PublicAiModelOut(
            id=m.id,
            name=m.name,
            provider=m.provider,
            model_name=m.model_name,
            is_default=m.is_default,
            subjects=sorted(list(subj_map.get(m.id, set()))),
        )
        for m in models
    ]


@router.post("/teacher/kb/upload", include_in_schema=False)
async def teacher_upload_kb(
    subject: str = Form(""),
    title: str = Form(""),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "teacher":
        raise HTTPException(status_code=403, detail="Not authorized")

    meta = await _save_upload(file, _TEACHER_UPLOAD_DIR)
    obj = TeacherKnowledgeBaseDocument(
        owner_user_id=current_user.id,
        subject=(subject or "").strip(),
        title=(title or file.filename or "").strip() or "未命名文档",
        original_filename=file.filename or meta["stored_filename"],
        stored_filename=meta["stored_filename"],
        url=meta["url"],
        file_ext=meta["file_ext"],
        file_size=meta["file_size"],
    )
    db.add(obj)
    await db.commit()
    return {"ok": True, "url": obj.url, "id": obj.id}


@router.post("/student/course-ai/select", response_model=StudentCourseAiSelectOut, include_in_schema=False)
async def student_select_course_ai(
    payload: StudentCourseAiSelectRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="Not authorized")

    course_id = int(payload.course_id)
    model_api_id = int(payload.model_api_id) if payload.model_api_id else None

    existing = (await db.execute(
        select(StudentCourseAiSelection).where(
            StudentCourseAiSelection.student_user_id == current_user.id,
            StudentCourseAiSelection.course_id == course_id,
        )
    )).scalars().first()

    if existing:
        existing.model_api_id = model_api_id
    else:
        db.add(StudentCourseAiSelection(student_user_id=current_user.id, course_id=course_id, model_api_id=model_api_id))

    await db.commit()
    return StudentCourseAiSelectOut(course_id=course_id, model_api_id=model_api_id)

