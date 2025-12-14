@echo off
setlocal EnableExtensions EnableDelayedExpansion

:: Define Root Directory (remove trailing slash)
set "SCRIPT_DIR=%~dp0"
if "%SCRIPT_DIR:~-1%"=="\" set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"
set "ROOT_DIR=%SCRIPT_DIR%"

set "BACKEND_DIR=%ROOT_DIR%\backend"
set "FRONTEND_DIR=%ROOT_DIR%\frontend"
set "BACKEND_PORT=8000"
set "FRONTEND_PORT=2003"
set "BACKEND_HEALTH_URL=http://127.0.0.1:%BACKEND_PORT%/api/health"

echo [INFO] Project Root: "%ROOT_DIR%"
echo [INFO] Backend Dir : "%BACKEND_DIR%"
echo [INFO] Frontend Dir: "%FRONTEND_DIR%"

:: Check Backend Environment
if not exist "%BACKEND_DIR%\venv\Scripts\python.exe" (
    echo [ERROR] Python virtual environment not found at "%BACKEND_DIR%\venv"
    echo         Please run: cd backend ^&^& python -m venv venv ^&^& venv\Scripts\pip install -r requirements.txt
    pause
    exit /b 1
)

:: Check Frontend Environment
if not exist "%FRONTEND_DIR%\node_modules" (
    echo [ERROR] node_modules not found in "%FRONTEND_DIR%"
    echo         Please run: cd frontend ^&^& npm install
    pause
    exit /b 1
)

:: Try probing backend health before launching
call :probe_service "%BACKEND_HEALTH_URL%"
if !errorlevel!==0 (
    echo [INFO] Backend already responding on %BACKEND_HEALTH_URL%, skipping restart.
) else (
    call :check_port %BACKEND_PORT%
    if !errorlevel!==0 (
        echo [INFO] Starting Backend on port %BACKEND_PORT%...
        start "Backend_%BACKEND_PORT%" cmd /k "cd /d ""%BACKEND_DIR%"" && venv\Scripts\python -m uvicorn app.main:socket_app --reload --host 0.0.0.0 --port %BACKEND_PORT%"
    ) else (
        echo [WARN] Port %BACKEND_PORT% is already in use. Skipping Backend start.
    )
)

:: Start Frontend
call :check_port %FRONTEND_PORT%
if !errorlevel!==0 (
    echo [INFO] Starting Frontend on port %FRONTEND_PORT%...
    start "Frontend_%FRONTEND_PORT%" cmd /k "cd /d ""%FRONTEND_DIR%"" && npm run dev -- --host 0.0.0.0 --port %FRONTEND_PORT%"
) else (
    echo [WARN] Port %FRONTEND_PORT% is already in use. Skipping Frontend start.
)

:: Wait for services
echo.
echo [INFO] Services are starting...
echo Frontend: http://localhost:%FRONTEND_PORT%/
echo Backend : http://localhost:%BACKEND_PORT%/docs
echo.
echo Press any key to exit this launcher (services will keep running).
pause >nul
exit /b 0

:check_port
powershell -NoLogo -NoProfile -Command "if (Get-NetTCPConnection -State Listen -LocalPort %1 -ErrorAction SilentlyContinue) { exit 0 } else { exit 1 }" >nul 2>&1
if !errorlevel!==0 exit /b 1
exit /b 0

:probe_service
powershell -NoLogo -NoProfile -Command "try {Invoke-WebRequest -UseBasicParsing -Uri '%~1' -TimeoutSec 2 ^| Out-Null; exit 0} catch { exit 1 }"
exit /b %errorlevel%
