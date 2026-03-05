@echo off
title FakeBuster AI
echo.
echo  ══════════════════════════════════════
echo   FakeBuster AI — Starting Servers...
echo  ══════════════════════════════════════
echo.

:: Start backend (port 8000)
echo [1/2] Starting Backend on http://localhost:8000 ...
cd /d "%~dp0backend"
start "FakeBuster Backend" cmd /k ".\venv\Scripts\python.exe -m uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8000 --reload"

:: Start frontend (port 3000)
echo [2/2] Starting Frontend on http://localhost:3000 ...
cd /d "%~dp0frontend"
start "FakeBuster Frontend" cmd /k "python -m http.server 3000"

:: Wait and open browser
timeout /t 3 /nobreak >nul
start http://localhost:3000

echo.
echo  ✓ Backend:  http://localhost:8000/docs
echo  ✓ Frontend: http://localhost:3000
echo.
echo  Close this window anytime. The servers run in separate windows.
echo.
pause
