@echo off
rem Starts the GreenOps backend and frontend in two windows and opens the app.
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo Python environment not found at .venv. Create it first: python -m venv .venv
  pause
  exit /b 1
)
if not exist "frontend\node_modules" (
  echo Installing frontend packages. This runs once.
  call npm --prefix frontend ci
)

start "GreenOps backend (port 8000)" cmd /k ".venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000"
start "GreenOps frontend (port 5173)" cmd /k "npm --prefix frontend run dev"

rem Give both servers a few seconds before opening the browser.
timeout /t 8 /nobreak >nul
start "" http://localhost:5173
