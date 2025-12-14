from fastapi import FastAPI, APIRouter, Request
from fastapi.middleware.cors import CORSMiddleware
from .routers import (
    ai_qa,
    analysis,
    attendance,
    auth,
    calendar,
    cert,
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
from .database import AsyncSessionLocal
from .models.user import User, UserProfile
from .models.admin import Admin
from .models.course import Teacher
from .models.student import Student
from .dependencies.auth import get_password_hash

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
else:
    socket_app = app

# Create tables on startup (for dev purposes)
@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
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
        await db.commit()

_routers = [
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
