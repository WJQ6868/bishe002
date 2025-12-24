@echo off
chcp 65001
echo =======================================================
echo       正在启动高校智能教务系统 (Smart University System)
echo =======================================================

echo [1/3] 正在启动后端服务 (FastAPI + Socket.IO)...
start "Backend Service" cmd /k "cd backend && ..\.venv\Scripts\python.exe -m uvicorn app.main:socket_app --reload --host 0.0.0.0 --port 8000"

echo [2/3] 正在启动前端服务 (Vite)...
start "Frontend Service" cmd /k "cd frontend && npm run dev"

echo [3/3] 等待服务就绪...
timeout /t 5 >nul

echo 正在打开浏览器...
start http://localhost:2003

echo =======================================================
echo       系统启动成功！
echo       前端地址: http://localhost:2003
echo       后端地址: http://localhost:8000
echo       请勿关闭弹出的命令行窗口
echo =======================================================
pause
