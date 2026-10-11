@echo off
setlocal
cd /d "%~dp0"

 echo ======================================
 echo Starting Energy Diagnostic System
 echo ======================================
 echo.

 if not exist "backend\venv\Scripts\python.exe" (
   echo ERROR: Backend virtual environment is missing.
   echo Create backend\venv and install backend\requirements.txt first.
   pause
   exit /b 1
 )

 start "Energy Diagnostics Backend" cmd /k "cd /d ""%~dp0backend"" && ""%~dp0backend\venv\Scripts\python.exe"" api.py"
 timeout /t 6 > nul

 if not exist "frontend\node_modules" (
   echo ERROR: Frontend dependencies are missing. Run npm install in frontend first.
   pause
   exit /b 1
 )
 start "Energy Diagnostics Frontend" cmd /k "cd /d ""%~dp0frontend"" && npm run dev"
 timeout /t 5 > nul
 start "" "http://localhost:5173"

 echo.
 echo ======================================
 echo  Application Started!
 echo  Backend:  http://localhost:8000
 echo  Frontend: http://localhost:5173
 echo ======================================