@echo off
cd /d "%~dp0"

echo ======================================
echo Starting Energy Diagnostic System
echo ======================================
echo.

REM -------- BACKEND --------
echo Starting Backend...
start cmd /k "cd backend && venv\Scripts\activate && python api.py"

REM Wait longer for backend to fully start
timeout /t 6 > nul

REM -------- PRE-WARM PIPELINE --------
echo Pre-warming pipeline...
curl -s -X POST http://localhost:8000/api/pipeline/run > nul

REM -------- FRONTEND --------
echo Starting Frontend...
start cmd /k "cd frontend && npm run dev"

timeout /t 6 > nul

REM -------- AUTO OPEN BROWSER --------
start "" "http://localhost:5173"

echo.
echo Application Started! Pipeline warming in background...