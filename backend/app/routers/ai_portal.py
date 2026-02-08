from __future__ import annotations

import json
import os
import re
import uuid
import time
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, Body
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..dependencies.auth import get_current_user
from ..models.ai_config import (
    ALLOWED_KB_EXTS,
    AiKnowledgeBase,
    AiKnowledgeBaseDocument,
    AiKnowledgeBaseSubject,
    AiLessonPlanTask,
    AiModelApi,
    AiUsageLog,
    AiWorkflowApp,
    StudentCourseAiFavorite,
    StudentCourseAiSelection,
    TeacherKnowledgeBaseDocument,
)
from ..models.course import Course
from ..models.user import User
from ..schemas.ai_portal import (
    LessonPlanTaskCreate,
    LessonPlanTaskOut,
    LessonPlanTaskResultUpdate,
    PublicAiModelApiOut,
    StudentCourseAiFavoriteRequest,
    StudentCourseAiItemOut,
    StudentCourseAiSelectRequest,
    TeacherCourseOut,
    TeacherKbDocumentOut,
    TeacherKbUpdateRequest,
)
from ..schemas.admin_ai import AiWorkflowAppOut, AiCustomerServiceSettingsOut
from ..services.ai_workflow import delete_document_chunks, extract_text_from_file, rebuild_document_chunks

router = APIRouter(prefix="/ai", tags=["AI Portal"])


def _customer_service_default_settings() -> dict:
    return {
        "welcome_str": "你好，我是AI客服，可以帮你解答校园常见问题。",
        "recommend_questions": ["如何请假？", "如何选课？", "成绩在哪里查询？"],
        "search_placeholder": "请输入问题，例如：如何请假？",
        "system_prompt_template": None,
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
    if out.get("system_prompt_template") is not None and not isinstance(out.get("system_prompt_template"), str):
        out["system_prompt_template"] = None
    return out


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", (value or "").strip().lower())
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    return slug or uuid.uuid4().hex[:8]


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


async def _load_app_by_code(db: AsyncSession, code: str) -> Optional[AiWorkflowApp]:
    return (
        await db.execute(select(AiWorkflowApp).where(AiWorkflowApp.code == code))
    ).scalars().first()


async def _ensure_teacher_course_kb(
    db: AsyncSession,
    *,
    teacher_user_id: int,
    course_id: Optional[int],
) -> AiKnowledgeBase:
    if course_id:
        slug = f"course-{course_id}"
        name = f"课程{course_id}知识库"
        owner_type = "course"
    else:
        slug = f"teacher-{teacher_user_id}"
        name = "教师私有知识库"
        owner_type = "teacher"
    kb = (await db.execute(select(AiKnowledgeBase).where(AiKnowledgeBase.slug == slug))).scalars().first()
    if kb:
        return kb
    kb = AiKnowledgeBase(
        slug=_slugify(slug),
        name=name,
        owner_type=owner_type,
        owner_user_id=teacher_user_id,
        course_id=course_id,
        feature="course_assistant",
        is_default=False,
    )
    db.add(kb)
    await db.commit()
    await db.refresh(kb)
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


async def _load_customer_service_settings_from_app(db: AsyncSession) -> dict:
    app = await _get_or_create_app(db, code="customer_service", name="AI客户服务", app_type="customer_service")
    payload = _load_json_settings(app.settings_json)
    return _normalize_customer_service_settings(payload)


def _lesson_plan_task_to_out(task: AiLessonPlanTask) -> LessonPlanTaskOut:
    return LessonPlanTaskOut(
        id=task.id,
        title=task.title,
        outline=task.outline,
        course_id=task.course_id,
        status=task.status,
        result=task.result,
        error_message=task.error_message,
        knowledge_base_id=task.knowledge_base_id,
        model_api_id=task.model_api_id,
        created_at=task.created_at,
        updated_at=task.updated_at,
        completed_at=task.completed_at,
    )


async def _load_teacher_task(db: AsyncSession, teacher_id: int, task_id: int) -> AiLessonPlanTask:
    task = (
        await db.execute(
            select(AiLessonPlanTask).where(
                AiLessonPlanTask.id == task_id,
                AiLessonPlanTask.teacher_user_id == teacher_id,
            )
        )
    ).scalars().first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task


# ---------------- Public: customer service config ----------------

@router.get("/customer-service/config", response_model=AiCustomerServiceSettingsOut)
async def get_customer_service_config(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    settings = await _load_customer_service_settings_from_app(db)
    return AiCustomerServiceSettingsOut(**settings)

@router.get("/customer-service/apps", response_model=List[AiWorkflowAppOut])
async def list_customer_service_apps(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    res = await db.execute(
        select(AiWorkflowApp)
        .where(AiWorkflowApp.type == "customer_service", AiWorkflowApp.status == "enabled")
        .order_by(AiWorkflowApp.updated_at.desc().nullslast(), AiWorkflowApp.id.desc())
    )
    apps = res.scalars().all()
    items: List[AiWorkflowAppOut] = []
    for app in apps:
        items.append(
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
    return items

@router.get("/course-assistant/apps", response_model=List[AiWorkflowAppOut])
async def list_course_assistant_apps(
    course_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(AiWorkflowApp).where(
        AiWorkflowApp.type == "course_assistant",
        AiWorkflowApp.status == "enabled",
    )
    if course_id is not None:
        stmt = stmt.where((AiWorkflowApp.course_id == course_id) | (AiWorkflowApp.course_id == None))  # type: ignore
    stmt = stmt.order_by(AiWorkflowApp.updated_at.desc().nullslast(), AiWorkflowApp.id.desc())
    res = await db.execute(stmt)
    apps = res.scalars().all()
    items: List[AiWorkflowAppOut] = []
    for app in apps:
        items.append(
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
    return items


# ---------- Teacher-owned course assistant workflows ----------

@router.get("/teacher/course-assistant/apps", response_model=List[AiWorkflowAppOut])
async def list_teacher_course_assistant_apps(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "teacher":
        raise HTTPException(status_code=403, detail="仅教师可操作")
    res = await db.execute(
        select(AiWorkflowApp)
        .where(
            AiWorkflowApp.type == "course_assistant",
            AiWorkflowApp.owner_user_id == current_user.id,
        )
        .order_by(AiWorkflowApp.updated_at.desc().nullslast(), AiWorkflowApp.id.desc())
    )
    apps = res.scalars().all()
    return [
        AiWorkflowAppOut(
            code=a.code,
            type=a.type,
            name=a.name,
            status=a.status,
            knowledge_base_id=a.knowledge_base_id,
            model_api_id=a.model_api_id,
            owner_user_id=a.owner_user_id,
            course_id=a.course_id,
            settings=_load_json_settings(a.settings_json),
            updated_at=a.updated_at,
        )
        for a in apps
    ]


@router.post("/teacher/course-assistant/apps", response_model=AiWorkflowAppOut)
async def create_teacher_course_assistant_app(
    name: str = Body(..., embed=True),
    base_code: str = Body(..., embed=True),
    course_id: Optional[int] = Body(None, embed=True),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "teacher":
        raise HTTPException(status_code=403, detail="仅教师可操作")

    base_app = (
        await db.execute(
            select(AiWorkflowApp).where(
                AiWorkflowApp.code == base_code,
                AiWorkflowApp.type == "course_assistant",
                AiWorkflowApp.status == "enabled",
            )
        )
    ).scalars().first()
    if not base_app:
        raise HTTPException(status_code=404, detail="基础工作流不存在或未启用")

    code = f"tca-{current_user.id}-{int(time.time())}"
    new_app = AiWorkflowApp(
        code=code,
        type="course_assistant",
        name=name.strip() or base_app.name,
        status="enabled",
        knowledge_base_id=base_app.knowledge_base_id,
        model_api_id=base_app.model_api_id,
        owner_user_id=current_user.id,
        course_id=course_id,
        settings_json=base_app.settings_json,
    )
    db.add(new_app)
    await db.commit()
    await db.refresh(new_app)
    return AiWorkflowAppOut(
        code=new_app.code,
        type=new_app.type,
        name=new_app.name,
        status=new_app.status,
        knowledge_base_id=new_app.knowledge_base_id,
        model_api_id=new_app.model_api_id,
        owner_user_id=new_app.owner_user_id,
        course_id=new_app.course_id,
        settings=_load_json_settings(new_app.settings_json),
        updated_at=new_app.updated_at,
    )


@router.put("/teacher/course-assistant/apps/{code}", response_model=AiWorkflowAppOut)
async def update_teacher_course_assistant_app(
    code: str,
    name: Optional[str] = Body(None, embed=True),
    course_id: Optional[int] = Body(None, embed=True),
    status: Optional[str] = Body(None, embed=True),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "teacher":
        raise HTTPException(status_code=403, detail="仅教师可操作")
    app = (
        await db.execute(
            select(AiWorkflowApp).where(
                AiWorkflowApp.code == code,
                AiWorkflowApp.owner_user_id == current_user.id,
                AiWorkflowApp.type == "course_assistant",
            )
        )
    ).scalars().first()
    if not app:
        raise HTTPException(status_code=404, detail="工作流不存在")
    if name is not None:
        app.name = name.strip() or app.name
    if course_id is not None:
        app.course_id = course_id
    if status in {"enabled", "disabled"}:
        app.status = status
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


@router.delete("/teacher/course-assistant/apps/{code}")
async def delete_teacher_course_assistant_app(
    code: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "teacher":
        raise HTTPException(status_code=403, detail="仅教师可操作")
    app = (
        await db.execute(
            select(AiWorkflowApp).where(
                AiWorkflowApp.code == code,
                AiWorkflowApp.owner_user_id == current_user.id,
                AiWorkflowApp.type == "course_assistant",
            )
        )
    ).scalars().first()
    if not app:
        return {"ok": True}
    await db.delete(app)
    await db.commit()
    return {"ok": True}

_TEACHER_UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "uploads", "kb_teacher")
os.makedirs(_TEACHER_UPLOAD_DIR, exist_ok=True)


def _ensure_ext(filename: str) -> str:
    ext = os.path.splitext(filename or "")[1].lower()
    if ext not in ALLOWED_KB_EXTS:
        raise HTTPException(status_code=400, detail=f"不支持的文件格式: {ext}")
    return ext


async def _save_upload(file: UploadFile) -> dict:
    ext = _ensure_ext(file.filename)
    stored = f"{uuid.uuid4().hex}{ext}"
    abs_path = os.path.join(_TEACHER_UPLOAD_DIR, stored)

    data = await file.read()
    with open(abs_path, "wb") as f:
        f.write(data)

    rel_url = "/static/uploads/kb_teacher/" + stored
    return {
        "stored_filename": stored,
        "file_ext": ext,
        "file_size": len(data),
        "url": rel_url,
        "abs_path": abs_path,
    }


# ---------------- 公共：启用模型列表 ----------------
@router.get("/public/model-apis", response_model=List[PublicAiModelApiOut])
async def list_public_model_apis(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    res = await db.execute(select(AiModelApi).where(AiModelApi.enabled == True).order_by(AiModelApi.is_default.desc(), AiModelApi.id.desc()))
    items = []
    for o in res.scalars().all():
        items.append(
            PublicAiModelApiOut(
                id=o.id,
                name=o.name,
                provider=o.provider,
                model_name=o.model_name,
                endpoint=o.endpoint,
                enabled=o.enabled,
                is_default=o.is_default,
                updated_at=o.updated_at,
            )
        )
    return items


# ---------------- 教师：课程列表（用于绑定KB） ----------------
@router.get("/teacher/courses", response_model=List[TeacherCourseOut])
async def list_teacher_courses(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != "teacher":
        raise HTTPException(status_code=403, detail="Only teachers can access")

    # sys_users.username 对应 teacher_id
    res = await db.execute(select(Course).where(Course.teacher_id == current_user.username).order_by(Course.id.desc()))
    return [TeacherCourseOut(id=c.id, name=c.name) for c in res.scalars().all()]


# ---------------- 教师：私有知识库 CRUD ----------------
@router.get("/teacher/kb/documents", response_model=List[TeacherKbDocumentOut])
async def list_teacher_kb_documents(
    course_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "teacher":
        raise HTTPException(status_code=403, detail="Only teachers can access")

    kb = await _ensure_teacher_course_kb(db, teacher_user_id=current_user.id, course_id=course_id)
    stmt = (
        select(AiKnowledgeBaseDocument)
        .options(selectinload(AiKnowledgeBaseDocument.subject))
        .where(AiKnowledgeBaseDocument.knowledge_base_id == kb.id)
        .order_by(AiKnowledgeBaseDocument.updated_at.desc().nullslast(), AiKnowledgeBaseDocument.id.desc())
    )
    res = await db.execute(stmt)
    docs = res.scalars().all()
    out: List[TeacherKbDocumentOut] = []
    for doc in docs:
        out.append(
            TeacherKbDocumentOut(
                id=doc.id,
                course_id=kb.course_id,
                subject=doc.subject.name if getattr(doc, "subject", None) else "",
                title=doc.title,
                original_filename=doc.original_filename,
                url=doc.url,
                file_ext=doc.file_ext,
                file_size=doc.file_size,
                created_at=doc.created_at,
                updated_at=doc.updated_at,
            )
        )
    return out


@router.post("/teacher/kb/upload", response_model=TeacherKbDocumentOut)
async def upload_teacher_kb(
    title: str = Form(...),
    subject: str = Form(""),
    course_id: Optional[int] = Form(None),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "teacher":
        raise HTTPException(status_code=403, detail="Only teachers can access")

    if course_id is not None:
        # 只能绑定自己教授的课程
        c = (await db.execute(select(Course).where(Course.id == course_id))).scalars().first()
        if not c:
            raise HTTPException(status_code=404, detail="Course not found")
        if str(c.teacher_id) != str(current_user.username):
            raise HTTPException(status_code=403, detail="Not your course")

    kb = await _ensure_teacher_course_kb(db, teacher_user_id=current_user.id, course_id=course_id)
    subject_obj = await _ensure_subject_for_kb(db, kb, subject or None)
    saved = await _save_upload(file)

    doc = AiKnowledgeBaseDocument(
        knowledge_base_id=kb.id,
        subject_id=subject_obj.id,
        title=(title or file.filename or "").strip() or "未命名文档",
        original_filename=file.filename or saved["stored_filename"],
        stored_filename=saved["stored_filename"],
        url=saved["url"],
        file_ext=saved["file_ext"],
        file_size=saved["file_size"],
        uploaded_by_admin=str(current_user.username),
        enabled=True,
    )
    db.add(doc)
    await db.flush()
    text = extract_text_from_file(saved["abs_path"], saved["file_ext"])
    await rebuild_document_chunks(db, doc, text)
    await db.commit()
    await db.refresh(doc)

    return TeacherKbDocumentOut(
        id=doc.id,
        course_id=kb.course_id,
        subject=subject_obj.name,
        title=doc.title,
        original_filename=doc.original_filename,
        url=doc.url,
        file_ext=doc.file_ext,
        file_size=doc.file_size,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
    )


@router.put("/teacher/kb/documents/{doc_id}", response_model=TeacherKbDocumentOut)
async def update_teacher_kb_document(
    doc_id: int,
    payload: TeacherKbUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "teacher":
        raise HTTPException(status_code=403, detail="Only teachers can access")

    doc = (
        await db.execute(select(AiKnowledgeBaseDocument).where(AiKnowledgeBaseDocument.id == doc_id))
    ).scalars().first()
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    kb = (
        await db.execute(select(AiKnowledgeBase).where(AiKnowledgeBase.id == doc.knowledge_base_id))
    ).scalars().first()
    if not kb or kb.owner_user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not allowed")

    if payload.course_id is not None and payload.course_id != kb.course_id:
        c = (await db.execute(select(Course).where(Course.id == payload.course_id))).scalars().first()
        if not c:
            raise HTTPException(status_code=404, detail="Course not found")
        if str(c.teacher_id) != str(current_user.username):
            raise HTTPException(status_code=403, detail="Not your course")
        kb.course_id = payload.course_id

    if payload.title is not None:
        doc.title = payload.title.strip() or doc.title

    await db.commit()
    await db.refresh(doc)
    return TeacherKbDocumentOut(
        id=doc.id,
        course_id=kb.course_id,
        subject=payload.subject or "",
        title=doc.title,
        original_filename=doc.original_filename,
        url=doc.url,
        file_ext=doc.file_ext,
        file_size=doc.file_size,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
    )


@router.post("/teacher/kb/documents/{doc_id}/replace", response_model=TeacherKbDocumentOut)
async def replace_teacher_kb_document(
    doc_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "teacher":
        raise HTTPException(status_code=403, detail="Only teachers can access")

    doc = (
        await db.execute(select(AiKnowledgeBaseDocument).where(AiKnowledgeBaseDocument.id == doc_id))
    ).scalars().first()
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    kb = (
        await db.execute(select(AiKnowledgeBase).where(AiKnowledgeBase.id == doc.knowledge_base_id))
    ).scalars().first()
    if not kb or kb.owner_user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not allowed")

    saved = await _save_upload(file)
    try:
        if doc.stored_filename:
            old = os.path.join(_TEACHER_UPLOAD_DIR, doc.stored_filename)
            if os.path.isfile(old):
                os.remove(old)
    except Exception:
        pass

    doc.original_filename = file.filename or saved["stored_filename"]
    doc.stored_filename = saved["stored_filename"]
    doc.url = saved["url"]
    doc.file_ext = saved["file_ext"]
    doc.file_size = saved["file_size"]

    text = extract_text_from_file(saved["abs_path"], saved["file_ext"])
    await rebuild_document_chunks(db, doc, text)
    await db.commit()
    await db.refresh(doc)

    return TeacherKbDocumentOut(
        id=doc.id,
        course_id=kb.course_id,
        subject="",
        title=doc.title,
        original_filename=doc.original_filename,
        url=doc.url,
        file_ext=doc.file_ext,
        file_size=doc.file_size,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
    )


@router.delete("/teacher/kb/documents/{doc_id}")
async def delete_teacher_kb_document(
    doc_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "teacher":
        raise HTTPException(status_code=403, detail="Only teachers can access")

    doc = (
        await db.execute(select(AiKnowledgeBaseDocument).where(AiKnowledgeBaseDocument.id == doc_id))
    ).scalars().first()
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    kb = (
        await db.execute(select(AiKnowledgeBase).where(AiKnowledgeBase.id == doc.knowledge_base_id))
    ).scalars().first()
    if not kb or kb.owner_user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not allowed")

    try:
        old = os.path.join(_TEACHER_UPLOAD_DIR, doc.stored_filename)
        if os.path.isfile(old):
            os.remove(old)
    except Exception:
        pass

    await delete_document_chunks(db, doc.id)
    await db.delete(doc)
    await db.commit()
    return {"ok": True}


# ---------------- 学生：专属课程 AI 列表 / 选择 / 收藏 ----------------


# ---------------- ????????? ----------------

@router.get("/teacher/lesson-plan/tasks", response_model=List[LessonPlanTaskOut])
async def list_lesson_plan_tasks(
    course_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "teacher":
        raise HTTPException(status_code=403, detail="Only teachers can access")
    stmt = (
        select(AiLessonPlanTask)
        .where(AiLessonPlanTask.teacher_user_id == current_user.id)
        .order_by(AiLessonPlanTask.created_at.desc())
    )
    if course_id is not None:
        stmt = stmt.where(AiLessonPlanTask.course_id == course_id)
    res = await db.execute(stmt)
    return [_lesson_plan_task_to_out(task) for task in res.scalars().all()]


@router.post("/teacher/lesson-plan/tasks", response_model=LessonPlanTaskOut)
async def create_lesson_plan_task(
    payload: LessonPlanTaskCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "teacher":
        raise HTTPException(status_code=403, detail="Only teachers can access")
    title = (payload.title or "").strip()
    if not title:
        raise HTTPException(status_code=400, detail="标题不能为空")

    course_id = payload.course_id
    if course_id is not None:
        c = (await db.execute(select(Course).where(Course.id == course_id))).scalars().first()
        if not c:
            raise HTTPException(status_code=404, detail="Course not found")
        if str(c.teacher_id) != str(current_user.username):
            raise HTTPException(status_code=403, detail="Not your course")

    app = await _get_or_create_app(db, code="lesson_plan", name="智能教案", app_type="lesson_plan")
    task = AiLessonPlanTask(
        teacher_user_id=current_user.id,
        course_id=course_id,
        title=title,
        outline=(payload.outline or "").strip() or None,
        status="pending",
        knowledge_base_id=app.knowledge_base_id,
        model_api_id=app.model_api_id,
    )
    db.add(task)
    db.add(
        AiUsageLog(
            feature="lesson_plan",
            user_id=current_user.id,
            user_role=current_user.role,
            result="success",
        )
    )
    await db.commit()
    await db.refresh(task)
    return _lesson_plan_task_to_out(task)


@router.get("/teacher/lesson-plan/tasks/{task_id}", response_model=LessonPlanTaskOut)
async def get_lesson_plan_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "teacher":
        raise HTTPException(status_code=403, detail="Only teachers can access")
    task = await _load_teacher_task(db, current_user.id, task_id)
    return _lesson_plan_task_to_out(task)


@router.put("/teacher/lesson-plan/tasks/{task_id}/result", response_model=LessonPlanTaskOut)
async def update_lesson_plan_task_result(
    task_id: int,
    payload: LessonPlanTaskResultUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "teacher":
        raise HTTPException(status_code=403, detail="Only teachers can access")
    task = await _load_teacher_task(db, current_user.id, task_id)

    data = payload.model_dump(exclude_unset=True)
    if "status" in data and data["status"]:
        task.status = data["status"]
        if task.status == "completed":
            task.completed_at = datetime.utcnow()
        elif task.status in {"pending", "streaming"}:
            task.completed_at = None
    if "result" in data:
        task.result = data["result"]
    if "error_message" in data:
        task.error_message = data["error_message"]

    await db.commit()
    await db.refresh(task)
    return _lesson_plan_task_to_out(task)
@router.get("/student/course-ai/list", response_model=List[StudentCourseAiItemOut])
async def list_student_course_ais(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="Only students can access")

    # 复用 course router 的兼容逻辑：course_selections.student_id 可能存 username 或 sys_users.id
    from ..models.student import CourseSelection
    from ..models.course import Teacher

    student_keys = [str(current_user.username), str(current_user.id)]

    stmt = (
        select(Course, Teacher)
        .join(CourseSelection, Course.id == CourseSelection.course_id)
        .join(Teacher, Teacher.id == Course.teacher_id)
        .where(CourseSelection.student_id.in_(student_keys))
        .order_by(Course.id.desc())
    )
    res = await db.execute(stmt)

    # 预取选择与收藏
    sel_rows = (await db.execute(select(StudentCourseAiSelection).where(StudentCourseAiSelection.student_user_id == current_user.id))).scalars().all()
    sel_map = {int(s.course_id): s for s in sel_rows}

    fav_rows = (await db.execute(select(StudentCourseAiFavorite).where(StudentCourseAiFavorite.student_user_id == current_user.id))).scalars().all()
    fav_set = {int(f.course_id) for f in fav_rows}

    items: List[StudentCourseAiItemOut] = []
    for course, teacher in res.all():
        selection = sel_map.get(int(course.id))
        selected_model_api_id = selection.model_api_id if selection else None

        # 课程对应教师知识库更新时间（最新一条）
        kb_updated = (
            await db.execute(
                select(func.max(TeacherKnowledgeBaseDocument.updated_at))
                .where(TeacherKnowledgeBaseDocument.course_id == course.id)
            )
        ).scalar()

        items.append(
            StudentCourseAiItemOut(
                course_id=course.id,
                course_name=course.name,
                teacher_id=str(course.teacher_id) if course.teacher_id is not None else None,
                teacher_name=teacher.name if teacher else (str(course.teacher_id) if course.teacher_id else "未知教师"),
                teacher_kb_updated_at=kb_updated,
                selected_model_api_id=selected_model_api_id,
                favorite=int(course.id) in fav_set,
            )
        )

    return items


@router.put("/student/course-ai/select")
async def select_student_course_ai(
    payload: StudentCourseAiSelectRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="Only students can access")

    # 校验课程存在
    course = (await db.execute(select(Course).where(Course.id == payload.course_id))).scalars().first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    if payload.model_api_id is not None:
        model = (await db.execute(select(AiModelApi).where(AiModelApi.id == payload.model_api_id, AiModelApi.enabled == True))).scalars().first()
        if not model:
            raise HTTPException(status_code=404, detail="Model not found or disabled")

    obj = (
        await db.execute(
            select(StudentCourseAiSelection).where(
                StudentCourseAiSelection.student_user_id == current_user.id,
                StudentCourseAiSelection.course_id == payload.course_id,
            )
        )
    ).scalars().first()

    if not obj:
        obj = StudentCourseAiSelection(student_user_id=current_user.id, course_id=payload.course_id, model_api_id=payload.model_api_id)
        db.add(obj)
    else:
        obj.model_api_id = payload.model_api_id

    await db.commit()
    return {"ok": True}


@router.put("/student/course-ai/favorite")
async def favorite_student_course_ai(
    payload: StudentCourseAiFavoriteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="Only students can access")

    # 校验课程存在
    course = (await db.execute(select(Course).where(Course.id == payload.course_id))).scalars().first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    obj = (
        await db.execute(
            select(StudentCourseAiFavorite).where(
                StudentCourseAiFavorite.student_user_id == current_user.id,
                StudentCourseAiFavorite.course_id == payload.course_id,
            )
        )
    ).scalars().first()

    if payload.favorite:
        if not obj:
            db.add(StudentCourseAiFavorite(student_user_id=current_user.id, course_id=payload.course_id))
    else:
        if obj:
            await db.delete(obj)

    await db.commit()
    return {"ok": True}
