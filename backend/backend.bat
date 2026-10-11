@echo off
setlocal
 title Energy Diagnostics Backend

 echo ======================================
 echo   Starting Energy Diagnostic Backend
 echo ======================================
 echo.

 cd /d "%~dp0"
 if errorlevel 1 (
   echo ERROR: Could not enter the backend folder.
   pause
   exit /b 1
 )

 if not exist "venv\Scripts\python.exe" (
   echo ERROR: Backend virtual environment was not found at:
   echo   %~dp0venv\Scripts\python.exe
   echo Create it and install backend\requirements.txt before starting.
   pause
   exit /b 1
 )

 echo Starting FastAPI with the project virtual environment...
 echo Backend: http://localhost:8000
 echo.
 "venv\Scripts\python.exe" api.py
 set "APP_EXIT_CODE=%ERRORLEVEL%"
 if not "%APP_EXIT_CODE%"=="0" echo Backend exited with code %APP_EXIT_CODE%.
 pause
 exit /b %APP_EXIT_CODE%