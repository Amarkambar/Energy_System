@echo off
cd /d "%~dp0"

echo ======================================
echo  Energy Diagnostics System v1.0
echo ======================================
echo.

REM -------- FIND BACKEND --------
SET BACKEND=%~dp0backend
IF NOT EXIST "%BACKEND%\api.py" (
    echo  ERROR: backend\api.py not found. Please reinstall.
    pause & exit /b 1
)
echo  [OK] Backend: %BACKEND%

REM -------- START BACKEND --------
echo  Starting backend server...
IF EXIST "%BACKEND%\venv\Scripts\activate.bat" (
    start "Energy Diagnostics - Backend" cmd /k "cd /d "%BACKEND%" && venv\Scripts\activate && python api.py"
) ELSE (
    start "Energy Diagnostics - Backend" cmd /k "cd /d "%BACKEND%" && python api.py"
)

REM -------- WAIT FOR STARTUP --------
echo  Waiting for server to start...
timeout /t 7 > nul

REM -------- OPEN BROWSER --------
echo  Opening browser at http://localhost:8000
start "" "http://localhost:8000"

echo.
echo ======================================
echo  App running at http://localhost:8000
echo  Log in, then click "Run Pipeline"
echo  Close the backend window to stop.
echo ======================================
