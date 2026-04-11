@echo off
setlocal EnableDelayedExpansion
set "MODE=%~1"

cd /d "%~dp0"

if /I not "%MODE%"=="--serve-only" (
  echo [Backend] Preparing Python environment...

  if not exist ".venv\Scripts\python.exe" (
    echo [Backend] Creating virtual environment at backend\.venv ...
    set "VENV_BOOTSTRAP=py"
    where py >nul 2>nul
    if errorlevel 1 set "VENV_BOOTSTRAP=python"

    !VENV_BOOTSTRAP! -m venv .venv
    if errorlevel 1 (
      echo [Backend] Failed to create virtual environment.
      exit /b 1
    )
  )

  set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"

  if not exist ".env" if exist ".env.example" (
    copy /Y ".env.example" ".env" >nul
    echo [Backend] Created backend\.env from .env.example
  )

  echo [Backend] Syncing Python dependencies...
  "!PYTHON_EXE!" -m pip install --upgrade pip
  if errorlevel 1 exit /b 1

  "!PYTHON_EXE!" -m pip install -r requirements.txt
  if errorlevel 1 (
    echo [Backend] Dependency installation failed.
    exit /b 1
  )

  if /I "%MODE%"=="--prepare-only" (
    echo [Backend] Environment is ready.
    exit /b 0
  )
)

if not exist ".venv\Scripts\python.exe" (
  echo [Backend] Environment is missing. Run .\run_backend.bat --prepare-only first.
  exit /b 1
)

set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"

if not exist ".env" if exist ".env.example" (
  copy /Y ".env.example" ".env" >nul
  echo [Backend] Created backend\.env from .env.example
)

echo [Backend] Starting Flask server on http://localhost:5000 ...
"%PYTHON_EXE%" app.py
