@echo off
echo ============================================
echo   FireWatch AI - Forest Fire Detection System
echo ============================================
echo.
echo Starting Frontend (Vite) on http://localhost:5173 ...
cd /d "%~dp0frontend"
start "FireWatch Frontend" cmd /k "npm run dev"

echo Starting Backend (Flask) on http://localhost:5000 ...
cd /d "%~dp0backend"
start "FireWatch Backend" cmd /k "py app.py"

echo.
echo ============================================
echo   Both servers are starting!
echo   Frontend: http://localhost:5173
echo   Backend:  http://localhost:5000/api/
echo ============================================
echo.
timeout /t 5 /nobreak >nul
start http://localhost:5173
