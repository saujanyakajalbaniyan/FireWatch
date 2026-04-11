@echo off
setlocal
set "MODE=%~1"

cd /d "%~dp0"

if /I not "%MODE%"=="--serve-only" (
  echo [Frontend] Preparing Node environment...

  if not exist ".env" if exist ".env.example" (
    copy /Y ".env.example" ".env" >nul
    echo [Frontend] Created frontend\.env from .env.example
  )

  echo [Frontend] Syncing npm dependencies...
  call npm install --no-audit --no-fund
  if errorlevel 1 (
    echo [Frontend] npm install failed.
    exit /b 1
  )

  if /I "%MODE%"=="--prepare-only" (
    echo [Frontend] Environment is ready.
    exit /b 0
  )
)

if not exist ".env" if exist ".env.example" (
  copy /Y ".env.example" ".env" >nul
  echo [Frontend] Created frontend\.env from .env.example
)

echo [Frontend] Starting Vite dev server on http://localhost:5173 ...
call npm run dev
