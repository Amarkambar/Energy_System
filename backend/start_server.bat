@echo off
echo ============================================
echo   Energy Diagnostics - Backend Server
echo ============================================
echo.

:: Kill anything already on port 8000
echo [1/3] Clearing port 8000...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING 2^>nul') do (
    echo       Killing PID %%a
    taskkill /PID %%a /F >nul 2>&1
)
timeout /t 1 /nobreak >nul

:: Activate venv
echo [2/3] Activating virtual environment...
call venv\Scripts\activate.bat

:: Start server
echo [3/3] Starting API server on http://localhost:8000
echo.
echo  Swagger docs: http://localhost:8000/docs
echo  Health check: http://localhost:8000/api/health
echo.
echo  Press CTRL+C to stop.
echo ============================================
python -m uvicorn api:app --host 0.0.0.0 --port 8000 --reload
