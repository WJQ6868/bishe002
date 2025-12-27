from fastapi import FastAPI, APIRouter, Request
from fastapi.middleware.cors import CORSMiddleware
from .routers import (
    ai_qa,
    analysis,
    attendance,
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
    # 仅创建数据表，严格不写入任何模拟数据
    # 引入 Admin 模型以确保管理员表被创建
    from .models.admin import Admin  # noqa: F401
    async with AsyncSessionLocal() as db:
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
    ai_qa.router,
    analysis.router,
    message.router,   # 即时通讯路由
    friend.router,    # 好友管理路由
    leave.router,     # 请假管理路由
    attendance.router,
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
