from fastapi import FastAPI, APIRouter, Request
from fastapi.middleware.cors import CORSMiddleware
from .routers import (
    ai_qa,
    analysis,
    auth,
    calendar,
    cert,
    admin_teacher,
    admin_student,
    classroom,
    course,
    dashboard,
    data_sync,
    friend,
    homework,
    leave,
    log,
    message,
    quick_link,
    schedule,
    service,
    user,
    work,
    academic,
    admin_ai,
    ai_portal,
    teacher_grade,
)
from fastapi.staticfiles import StaticFiles
import os
from .database import engine, Base
from .logging_config import configure_logging
import logging
from sqlalchemy.future import select
from sqlalchemy import text, func
from .database import AsyncSessionLocal
from .models.user import User, UserProfile
from .models.admin import Admin
from .models.course import Teacher
from .models.student import Student
from .models import admin_user
from .dependencies.auth import get_password_hash
from .models.academic import AcademicCollege, AcademicMajor, AcademicClass, AcademicStudent, AcademicClassHeadTeacher
from .models import ai_config  # noqa: F401

# Configure logging at startup
configure_logging()
try:
    import socketio
    from .services.socket_manager import sio
except Exception:
    socketio = None
    sio = None

app = FastAPI(title="Smart University Academic Affairs System")


@app.middleware("http")
async def log_admin_user_list_auth(request: Request, call_next):
    if request.url.path.endswith("/admin/user/list"):
        logging.getLogger("auth").info(f"Auth header: {request.headers.get('authorization')}")
    response = await call_next(request)
    return response
# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:2003",
        "http://localhost:2003",
    ],
    allow_origin_regex=r"https?://.*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 创建 Socket.IO ASGI 应用（可选）
if socketio and sio:
    socket_app = socketio.ASGIApp(sio, app)
    print("[INFO] Socket.IO server initialized successfully - WebSocket support enabled")
else:
    socket_app = app
    print("[WARN] Socket.IO not available, using plain FastAPI app - WebSocket disabled")

# Create tables on startup (for dev purposes)
@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Ensure new columns for academic_majors in legacy DBs
        pragma_cols = await conn.execute(text("PRAGMA table_info('academic_majors')"))
        cols = [row[1] for row in pragma_cols]
        if "code" not in cols:
            await conn.execute(text("ALTER TABLE academic_majors ADD COLUMN code VARCHAR(20)"))
        if "status" not in cols:
            await conn.execute(text("ALTER TABLE academic_majors ADD COLUMN status INTEGER DEFAULT 1"))
        if "college_id" not in cols:
            await conn.execute(text("ALTER TABLE academic_majors ADD COLUMN college_id INTEGER"))
        if "update_time" not in cols:
            await conn.execute(text("ALTER TABLE academic_majors ADD COLUMN update_time DATETIME"))
            await conn.execute(text("UPDATE academic_majors SET update_time = create_time WHERE update_time IS NULL"))
        # Normalize empty strings to NULL on unique columns to avoid conflicts
        await conn.execute(text("UPDATE t_teacher SET email = NULL WHERE email = ''"))
        await conn.execute(text("UPDATE t_teacher SET mobile = NULL WHERE mobile = ''"))

        # Ensure new columns for academic_classes
        pragma_cols = await conn.execute(text("PRAGMA table_info('academic_classes')"))
        cols = [row[1] for row in pragma_cols]
        if "code" not in cols:
            await conn.execute(text("ALTER TABLE academic_classes ADD COLUMN code VARCHAR(30)"))
        if "status" not in cols:
            await conn.execute(text("ALTER TABLE academic_classes ADD COLUMN status INTEGER DEFAULT 1"))
        if "teacher_id" not in cols:
            await conn.execute(text("ALTER TABLE academic_classes ADD COLUMN teacher_id VARCHAR(20)"))
        if "update_time" not in cols:
            await conn.execute(text("ALTER TABLE academic_classes ADD COLUMN update_time DATETIME"))
            await conn.execute(text("UPDATE academic_classes SET update_time = create_time WHERE update_time IS NULL"))

        # Ensure new columns for academic_students
        pragma_cols = await conn.execute(text("PRAGMA table_info('academic_students')"))
        cols = [row[1] for row in pragma_cols]
        if "gender" not in cols:
            await conn.execute(text("ALTER TABLE academic_students ADD COLUMN gender INTEGER"))
        if "mobile" not in cols:
            await conn.execute(text("ALTER TABLE academic_students ADD COLUMN mobile VARCHAR(20)"))
        if "status" not in cols:
            await conn.execute(text("ALTER TABLE academic_students ADD COLUMN status INTEGER DEFAULT 1"))
        if "update_time" not in cols:
            await conn.execute(text("ALTER TABLE academic_students ADD COLUMN update_time DATETIME"))
            await conn.execute(text("UPDATE academic_students SET update_time = created_at WHERE update_time IS NULL"))

            # Ensure new columns for teacher_kb_documents (AI 教师私有知识库)
            pragma_cols = await conn.execute(text("PRAGMA table_info('teacher_kb_documents')"))
            cols = [row[1] for row in pragma_cols]
            if cols:  # 表存在时才做兼容升级
                if "course_id" not in cols:
                    await conn.execute(text("ALTER TABLE teacher_kb_documents ADD COLUMN course_id INTEGER"))
                if "updated_at" not in cols:
                    await conn.execute(text("ALTER TABLE teacher_kb_documents ADD COLUMN updated_at DATETIME"))
                    await conn.execute(text("UPDATE teacher_kb_documents SET updated_at = created_at WHERE updated_at IS NULL"))

        # Ensure new columns for ai_kb_subjects
        pragma_cols = await conn.execute(text("PRAGMA table_info('ai_kb_subjects')"))
        cols = [row[1] for row in pragma_cols]
        if cols:
            if "stage" not in cols:
                await conn.execute(text("ALTER TABLE ai_kb_subjects ADD COLUMN stage VARCHAR(50)"))
            if "enabled" not in cols:
                await conn.execute(text("ALTER TABLE ai_kb_subjects ADD COLUMN enabled BOOLEAN DEFAULT 1"))
                await conn.execute(text("UPDATE ai_kb_subjects SET enabled = 1 WHERE enabled IS NULL"))

        # Ensure new columns for ai_kb_documents
        pragma_cols = await conn.execute(text("PRAGMA table_info('ai_kb_documents')"))
        cols = [row[1] for row in pragma_cols]
        if cols:
            if "enabled" not in cols:
                await conn.execute(text("ALTER TABLE ai_kb_documents ADD COLUMN enabled BOOLEAN DEFAULT 1"))
                await conn.execute(text("UPDATE ai_kb_documents SET enabled = 1 WHERE enabled IS NULL"))
            if "updated_at" not in cols:
                await conn.execute(text("ALTER TABLE ai_kb_documents ADD COLUMN updated_at DATETIME"))
                await conn.execute(text("UPDATE ai_kb_documents SET updated_at = created_at WHERE updated_at IS NULL"))
            if "knowledge_base_id" not in cols:
                await conn.execute(text("ALTER TABLE ai_kb_documents ADD COLUMN knowledge_base_id INTEGER"))

        # Ensure new columns for ai_model_kb_links
        pragma_cols = await conn.execute(text("PRAGMA table_info('ai_model_kb_links')"))
        cols = [row[1] for row in pragma_cols]
        if cols:
            if "priority" not in cols:
                await conn.execute(text("ALTER TABLE ai_model_kb_links ADD COLUMN priority INTEGER DEFAULT 0"))
                await conn.execute(text("UPDATE ai_model_kb_links SET priority = 0 WHERE priority IS NULL"))

        # Ensure new columns for ai_model_apis
        pragma_cols = await conn.execute(text("PRAGMA table_info('ai_model_apis')"))
        cols = [row[1] for row in pragma_cols]
        if cols:
            if "api_header" not in cols:
                await conn.execute(text("ALTER TABLE ai_model_apis ADD COLUMN api_header TEXT"))
            if "api_version" not in cols:
                await conn.execute(text("ALTER TABLE ai_model_apis ADD COLUMN api_version VARCHAR(50)"))
            if "provider_brand" not in cols:
                await conn.execute(text("ALTER TABLE ai_model_apis ADD COLUMN provider_brand VARCHAR(50)"))
            if "temperature" not in cols:
                await conn.execute(text("ALTER TABLE ai_model_apis ADD COLUMN temperature FLOAT"))
            if "max_output_tokens" not in cols:
                await conn.execute(text("ALTER TABLE ai_model_apis ADD COLUMN max_output_tokens INTEGER"))

        # Ensure new columns for student_course_ai_selections
        pragma_cols = await conn.execute(text("PRAGMA table_info('student_course_ai_selections')"))
        cols = [row[1] for row in pragma_cols]
        if cols:
            if "custom_model_id" not in cols:
                await conn.execute(text("ALTER TABLE student_course_ai_selections ADD COLUMN custom_model_id INTEGER"))
    # 仅创建数据表，严格不写入任何模拟数据
    # 引入 Admin 模型以确保管理员表被创建
    from .models.admin import Admin  # noqa: F401
    async with AsyncSessionLocal() as db:
        # 内置 AI 模型 API 预设：幂等写入（不重复、不覆盖已有配置）。
        # API Key 建议通过环境变量注入，避免把密钥写进仓库。
        from .models.ai_config import AiKnowledgeBase, AiModelApi, AiWorkflowApp  # noqa: WPS433

        defaults = [
            {"username": "800001", "role": "admin", "name": "Admin Office", "dept": "Academic Affairs"},
            {"username": "100001", "role": "teacher", "name": "Teacher Zhang", "dept": "Computer Science"},
            {"username": "20230001", "role": "student", "name": "Student Li", "dept": "Computer Science", "grade": "2023"},
        ]
        for d in defaults:
            res = await db.execute(select(User).where(User.username == d["username"]))
            u = res.scalars().first()
            if not u:
                u = User(username=d["username"], password=get_password_hash("123456"), role=d["role"], is_active=True)
                db.add(u)
                await db.flush()
                profile = UserProfile(user_id=u.id, name=d["name"], dept=d.get("dept"), grade=d.get("grade"))
                db.add(profile)
                if d["role"] == "admin":
                    db.add(Admin(id=d["username"], name=d["name"], dept=d.get("dept")))
                elif d["role"] == "teacher":
                    db.add(Teacher(id=d["username"], name=d["name"]))
                elif d["role"] == "student":
                    db.add(Student(id=d["username"], name=d["name"], major=d.get("dept"), grade=d.get("grade")))
        await db.flush()

        # 同步新教职工/学生表数据，确保默认账号出现在新表
        # 教师
        teacher_exists = await db.execute(select(admin_user.TeacherUser).where(admin_user.TeacherUser.teacher_no == "100001"))
        if not teacher_exists.scalars().first():
            db.add(admin_user.TeacherUser(
                teacher_no="100001",
                name="Teacher Zhang",
                gender=1,
                dept_id=0,
                post_type=1,
                leave_status=1,
                status=1,
            ))
        # 学生
        student_exists = await db.execute(select(admin_user.StudentUser).where(admin_user.StudentUser.student_no == "20230001"))
        if not student_exists.scalars().first():
            db.add(admin_user.StudentUser(
                student_no="20230001",
                name="Student Li",
                gender=1,
                parent_mobile="",
                grade_id=2023,
                class_id=0,
                student_status=1,
                status=1,
            ))

        # 同步教师姓名到旧 teachers 表，供课程选教师使用
        teacher_rows = (await db.execute(select(admin_user.TeacherUser))).scalars().all()
        for t in teacher_rows:
            legacy = (await db.execute(select(Teacher).where(Teacher.id == t.teacher_no))).scalars().first()
            if legacy:
                legacy.name = t.name
            else:
                db.add(Teacher(id=t.teacher_no, name=t.name))

        # 同步学生姓名到旧 students 表，供课程/成绩等模块使用
        student_rows = (await db.execute(select(admin_user.StudentUser))).scalars().all()
        for s in student_rows:
            legacy_s = (await db.execute(select(Student).where(Student.id == s.student_no))).scalars().first()
            if legacy_s:
                legacy_s.name = s.name
                legacy_s.major = s.major
                legacy_s.grade = str(s.grade_id) if s.grade_id else legacy_s.grade
            else:
                db.add(Student(id=s.student_no, name=s.name, major=s.major, grade=str(s.grade_id) if s.grade_id else None))

        async def _ensure_ai_model_api(
            *,
            name: str,
            provider: str,
            model_name: str,
            endpoint: str,
            api_key_env: str | None,
            make_default_if_none: bool = False,
        ) -> None:
            ep = (endpoint or "").strip().rstrip("/")
            if not ep:
                return

            existed = (
                await db.execute(
                    select(AiModelApi).where(
                        AiModelApi.provider == provider,
                        AiModelApi.model_name == model_name,
                        AiModelApi.endpoint == ep,
                    )
                )
            ).scalars().first()

            env_key = (os.getenv(api_key_env) or "").strip() if api_key_env else ""

            if existed:
                # 若原本是占位 key 且环境变量提供了真实 key，则自动填充。
                if existed.api_key in {"", "__PLEASE_SET__", "__PLEASE_SET__ ", "__PLACEHOLDER__"} and env_key:
                    existed.api_key = env_key
                # 不自动启用，避免误用；由管理员在前端启用。
                return

            # 只有在系统里还没有任何默认模型时，才把预设标为默认。
            has_default = (
                await db.execute(select(func.count(AiModelApi.id)).where(AiModelApi.is_default == True))
            ).scalar() or 0
            is_default = bool(make_default_if_none and int(has_default) == 0)

            db.add(
                AiModelApi(
                    name=name,
                    provider=provider,
                    model_name=model_name,
                    endpoint=ep,
                    api_key=env_key or "__PLEASE_SET__",
                    timeout_seconds=30,
                    quota_per_hour=0,
                    enabled=False,
                    is_default=is_default,
                )
            )

        async def _ensure_ai_knowledge_base(
            *,
            slug: str,
            name: str,
            feature: str,
            owner_type: str = "system",
            is_default: bool = False,
        ) -> AiKnowledgeBase:
            existing = (
                await db.execute(select(AiKnowledgeBase).where(AiKnowledgeBase.slug == slug))
            ).scalars().first()
            if existing:
                return existing
            kb = AiKnowledgeBase(
                slug=slug,
                name=name,
                feature=feature,
                owner_type=owner_type,
                is_default=is_default,
            )
            db.add(kb)
            await db.flush()
            return kb

        async def _ensure_workflow_app(
            *,
            code: str,
            name: str,
            app_type: str,
            kb_slug: str | None = None,
        ) -> AiWorkflowApp:
            app = (await db.execute(select(AiWorkflowApp).where(AiWorkflowApp.code == code))).scalars().first()
            if app:
                return app
            kb_id = None
            if kb_slug:
                kb = (
                    await db.execute(select(AiKnowledgeBase).where(AiKnowledgeBase.slug == kb_slug))
                ).scalars().first()
                kb_id = kb.id if kb else None
            app = AiWorkflowApp(
                code=code,
                name=name,
                type=app_type,
                knowledge_base_id=kb_id,
                status="enabled",
            )
            db.add(app)
            await db.flush()
            return app

        # 预设清单（只放“后端已支持的 provider”）
        await _ensure_ai_model_api(
            name="通义千问（Qwen）",
            provider="dashscope_openai",
            model_name="qwen-plus",
            endpoint="https://dashscope.aliyuncs.com/compatible-mode/v1",
            api_key_env="AI_PRESET_DASHSCOPE_API_KEY",
            make_default_if_none=True,
        )
        await _ensure_ai_model_api(
            name="通义千问 Max（Qwen）",
            provider="dashscope_openai",
            model_name="qwen-max",
            endpoint="https://dashscope.aliyuncs.com/compatible-mode/v1",
            api_key_env="AI_PRESET_DASHSCOPE_API_KEY",
            make_default_if_none=False,
        )
        await _ensure_ai_model_api(
            name="火山方舟（Ark）",
            provider="ark_responses",
            model_name="deepseek-v3",
            endpoint="https://ark.cn-beijing.volces.com/api/v3",
            api_key_env="AI_PRESET_ARK_API_KEY",
            make_default_if_none=False,
        )

        kb_customer = await _ensure_ai_knowledge_base(
            slug="customer-service-base",
            name="客服知识库",
            feature="customer_service",
            is_default=True,
        )
        kb_course = await _ensure_ai_knowledge_base(
            slug="course-assistant-base",
            name="课程助手知识库",
            feature="course_assistant",
        )
        kb_lesson = await _ensure_ai_knowledge_base(
            slug="lesson-plan-base",
            name="智能教案知识库",
            feature="lesson_plan",
        )
        await db.commit()

        await _ensure_workflow_app(
            code="customer_service",
            name="AI客服",
            app_type="customer_service",
            kb_slug="customer-service-base",
        )
        await _ensure_workflow_app(
            code="course_assistant",
            name="AI课程助手",
            app_type="course_assistant",
            kb_slug="course-assistant-base",
        )
        await _ensure_workflow_app(
            code="lesson_plan",
            name="智能教案",
            app_type="lesson_plan",
            kb_slug="lesson-plan-base",
        )

        await db.commit()

        # Demo seed (disabled by default):
        # Only generate colleges/majors/classes/students when explicitly enabled.
        if os.getenv("ENABLE_DEMO_SEED") != "1":
            return

        # Seed academic college and majors
        college = (await db.execute(select(AcademicCollege).where(AcademicCollege.code == "CSSE"))).scalars().first()
        if not college:
            college = AcademicCollege(name="计算机与软件学院", code="CSSE", status=1)
            db.add(college)
            await db.flush()
        desired_majors = [
            ("计算机", "CS"),
            ("软件工程", "SE"),
            ("网络安全", "NS"),
            ("人工智能", "AI"),
            ("大数据", "BD"),
            ("工业互联网", "IIOT"),
        ]
        for name, code in desired_majors:
            major = (await db.execute(select(AcademicMajor).where((AcademicMajor.name == name) | (AcademicMajor.code == code)))).scalars().first()
            if not major:
                db.add(AcademicMajor(name=name, code=code, status=1, college_id=college.id))
            else:
                if not major.code and code:
                    major.code = code
                major.college_id = major.college_id or college.id
                major.status = 1

        # Persist academic seed (and any backfills)
        await db.commit()

        # Seed classes (2 per major) and students (5 per class)
        majors = (await db.execute(select(AcademicMajor).where(AcademicMajor.college_id == college.id))).scalars().all()
        majors_by_name = {m.name: m for m in majors}
        majors_by_code = {m.code: m for m in majors if m.code}

        class_plan = [
            ("计算机网络技术", "CSNT", [("计网2301", "计网2301"), ("计网2302", "计网2302")]),
            ("软件工程", "SE", [("软工2301", "软工2301"), ("软工2302", "软工2302")]),
            ("网络安全", "NS", [("网安2301", "网安2301"), ("网安2302", "网安2302")]),
            ("人工智能", "AI", [("AI2301", "AI2301"), ("AI2302", "AI2302")]),
            ("大数据", "BD", [("大数据2301", "大数据2301"), ("大数据2302", "大数据2302")]),
            ("工业互联网", "IIOT", [("工互2301", "工互2301"), ("工互2302", "工互2302")]),
        ]

        # Teacher binding: ensure 计网2301 binds 张敏 (fallback to first teacher)
        teacher_ids = [row[0] for row in (await db.execute(select(Teacher.id).order_by(Teacher.id))).all()]
        zhangmin = (await db.execute(select(Teacher).where(Teacher.name == "张敏"))).scalars().first()
        zhangmin_id = zhangmin.id if zhangmin else (teacher_ids[0] if teacher_ids else None)

        created_classes = []
        teacher_idx = 0
        for major_name, major_code, classes_for_major in class_plan:
            major = majors_by_name.get(major_name) or majors_by_code.get(major_code)
            if not major:
                continue
            for class_name, class_code in classes_for_major:
                exists = await db.execute(
                    select(AcademicClass).where(
                        (AcademicClass.major_id == major.id)
                        & (AcademicClass.name == class_name)
                    )
                )
                clazz = exists.scalars().first()
                if not clazz:
                    teacher_id = None
                    if class_name == "计网2301":
                        teacher_id = zhangmin_id
                    elif teacher_ids:
                        teacher_id = teacher_ids[teacher_idx % len(teacher_ids)]
                        teacher_idx += 1
                    clazz = AcademicClass(
                        major_id=major.id,
                        name=class_name,
                        code=class_code,
                        status=1,
                        teacher_id=teacher_id,
                        student_count=0,
                    )
                    db.add(clazz)
                    await db.flush()
                else:
                    # backfill
                    clazz.code = getattr(clazz, "code", None) or class_code
                    clazz.status = getattr(clazz, "status", 1) if getattr(clazz, "status", None) is not None else 1
                    if class_name == "计网2301" and not getattr(clazz, "teacher_id", None):
                        clazz.teacher_id = zhangmin_id
                created_classes.append(clazz)

        await db.commit()

        # Seed students: 5 per class
        mobile_samples = [
            "13800001234",
            "13900005678",
            "13700001111",
            "13600002222",
            "13500003333",
        ]
        name_samples = [
            ("张三", 1),
            ("李四", 2),
            ("王五", 1),
            ("赵六", 2),
            ("孙七", 1),
        ]
        # base codes per class name
        student_base = {
            "计网2301": 2301000,
            "计网2302": 2302000,
            "软工2301": 2311000,
            "软工2302": 2312000,
            "网安2301": 2321000,
            "网安2302": 2322000,
            "AI2301": 2331000,
            "AI2302": 2332000,
            "大数据2301": 2341000,
            "大数据2302": 2342000,
            "工互2301": 2351000,
            "工互2302": 2352000,
        }
        for clazz in created_classes:
            base = student_base.get(clazz.name)
            if not base:
                continue
            added = 0
            for i in range(5):
                stu_code = str(base + i + 1)
                exists = await db.execute(select(AcademicStudent).where(AcademicStudent.student_code == stu_code))
                if exists.scalars().first():
                    continue
                stu_name, gender = name_samples[i]
                db.add(
                    AcademicStudent(
                        class_id=clazz.id,
                        student_code=stu_code,
                        name=stu_name,
                        gender=gender,
                        mobile=mobile_samples[i],
                        status=1,
                    )
                )
                added += 1
            if added:
                clazz.student_count = (await db.execute(select(func.count(AcademicStudent.id)).where(AcademicStudent.class_id == clazz.id))).scalar() or 0

        await db.commit()

_routers = [
    admin_teacher.router,
    admin_student.router,
    course.router,
    schedule.router,
    academic.router,
    admin_ai.router,
    ai_qa.router,
    ai_portal.router,
    analysis.router,
    message.router,   # 即时通讯路由
    friend.router,    # 好友管理路由
    leave.router,     # 请假管理路由
    homework.router,
    work.router,
    calendar.router,
    service.router,
    dashboard.router,
    user.router,
    classroom.router,
    log.router,
    cert.router,
    auth.router,
    quick_link.router,
    quick_link.router_hyphen,
    data_sync.router,
    teacher_grade.router,
]

api_router = APIRouter(prefix="/api")
for router in _routers:
    app.include_router(router)
    api_router.include_router(router)

app.include_router(api_router)

if os.path.isdir("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    return {"message": "Welcome to the Smart University Academic Affairs System API"}

@app.get("/api/health")
async def health_check():
    return {"status": "ok"}

@app.get("/api/socketio/status")
async def socketio_status():
    """检查 Socket.IO 服务器状态"""
    from .services.socket_manager import online_users
    return {
        "socketio_enabled": socketio is not None and sio is not None,
        "online_users_count": len(online_users) if sio else 0,
        "message": "Socket.IO is enabled" if sio else "Socket.IO is not available"
    }
