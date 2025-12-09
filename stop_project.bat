@echo off
chcp 65001
echo =======================================================
echo       正在停止高校智能教务系统 (Smart University System)
echo =======================================================

echo [1/2] 正在停止后端服务 (Port 8000)...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000') do (
    echo 正在终止 PID: %%a
    taskkill /f /pid %%a >nul 2>&1
)

echo [2/2] 正在停止前端服务 (Port 2003)...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :2003') do (
    echo 正在终止 PID: %%a
    taskkill /f /pid %%a >nul 2>&1
)

echo.
echo 正在清理残留进程...
taskkill /F /IM node.exe >nul 2>&1
taskkill /F /IM uvicorn.exe >nul 2>&1
taskkill /F /IM python.exe >nul 2>&1

echo =======================================================
echo       系统已停止！
echo =======================================================
pause
