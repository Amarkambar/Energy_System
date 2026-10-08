@echo off
cd /d "%~dp0"

echo ======================================
echo  Starting Energy Diagnostic System
echo ======================================
echo.

REM -------- BACKEND --------
echo Starting Backend...
IF EXIST "%~dp0backend\venv\Scripts\activate.bat" (
    start cmd /k "cd /d "%~dp0backend" && venv\Scripts\activate && python api.py"
) ELSE (
    REM No venv — use system Python
    start cmd /k "cd /d "%~dp0backend" && python api.py"
)

REM Wait for backend to fully start
timeout /t 6 > nul

REM -------- PRE-WARM PIPELINE --------
echo Pre-warming pipeline...
curl -s -X POST http://localhost:8000/api/pipeline/run > nul 2>&1

REM -------- FRONTEND --------
echo Starting Frontend...
IF EXIST "%~dp0frontend\package.json" (
    start cmd /k "cd /d "%~dp0frontend" && npm run dev"
    timeout /t 6 > nul
    start "" "http://localhost:5173"
) ELSE (
    REM Installed mode: frontend served by backend on port 8000
    timeout /t 2 > nul
    start "" "http://localhost:8000"
)

echo.
echo ======================================
echo  Application Started!
echo  Pipeline warming in background...
echo ======================================
