@echo off
REM ==============================================================================
REM ETH Hunter & OneBrain - Start All with Looping Python & Playwright Chromium
REM Windows Batch Launcher
REM ==============================================================================

echo ======================================================
echo ⚡ ETH HUNTER & ONEBRAIN - START ALL (WINDOWS) ⚡
echo ======================================================

set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"

echo [1/4] Starting Backend API Server (Port 8000)...
start "ETH Hunter Backend" cmd /k "cd backend && python main.py"

timeout /t 2 >nul

echo [2/4] Starting Frontend Dashboard (Port 5173)...
start "ETH Hunter Frontend" cmd /k "cd frontend && npm run dev"

timeout /t 3 >nul

echo [3/4] Launching Google Chrome...
start http://localhost:5173

echo [4/4] Starting Continuous Looping Python & Playwright Worker...
python continuous_loop_worker.py --interval 30

pause
