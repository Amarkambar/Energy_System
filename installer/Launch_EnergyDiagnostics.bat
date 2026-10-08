@echo off
REM Energy Diagnostics — Windows Launcher
REM Starts the backend (which serves both API + React UI) and opens the browser

title Energy Diagnostics System
color 0A

echo.
echo  ============================================
echo   Energy Diagnostics System v1.0
echo  ============================================
echo.
echo  Starting server... please wait
echo.

REM Set working directory to where this launcher lives
cd /d "%~dp0"

REM Use bundled Python in app folder
SET PYTHON="%~dp0python\python.exe"
SET APP="%~dp0backend\api.py"

REM Check bundled Python exists
IF NOT EXIST %PYTHON% (
    echo  ERROR: Bundled Python not found.
    echo  Please reinstall Energy Diagnostics.
    pause
    exit /b 1
)

REM Create .env if it doesn't exist
IF NOT EXIST "%~dp0backend\.env" (
    echo JWT_SECRET=%RANDOM%%RANDOM%%RANDOM%> "%~dp0backend\.env"
    echo CORS_ORIGINS=http://localhost:8000>> "%~dp0backend\.env"
    echo MONGO_URI=>> "%~dp0backend\.env"
)

REM Install dependencies if first run (flag file check)
IF NOT EXIST "%~dp0backend\.installed" (
    echo  Installing dependencies (first run, please wait ~2 min)...
    %PYTHON% -m pip install -r "%~dp0backend\requirements.txt" --quiet --no-warn-script-location
    echo. > "%~dp0backend\.installed"
    echo  Dependencies installed!
)

REM Open browser after 4 seconds
start "" cmd /c "timeout /t 4 >nul && start http://localhost:8000"

REM Start FastAPI server (serving both API + React UI)
echo  Opening http://localhost:8000 in your browser...
echo  Press Ctrl+C to stop the server.
echo.
%PYTHON% -m uvicorn api:app --host 0.0.0.0 --port 8000 --workers 1 --app-dir "%~dp0backend"

pause
