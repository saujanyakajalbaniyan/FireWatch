@echo off
echo ============================================
echo   FireWatch AI - Forest Fire Detection System
echo ============================================
echo.
echo Starting Frontend (Vite) on http://localhost:5173 ...
start "FireWatch Frontend" cmd /k "cd /d \"%~dp0frontend\" && call run_frontend.bat"

echo Starting Backend (Flask) on http://localhost:5000 ...
start "FireWatch Backend" cmd /k "cd /d \"%~dp0backend\" && call run_backend.bat"

echo.
echo ============================================
echo   Both servers are starting!
echo   Frontend: http://localhost:5173
echo   Backend:  http://localhost:5000/api/
echo ============================================
echo.
timeout /t 5 /nobreak >nul
start http://localhost:5173
