@echo off
echo.
echo  Earth Intelligence Copilot
echo  ============================
echo.

cd /d "%~dp0backend"

:: Create venv if missing
if not exist "venv" (
    echo [INFO] Creating virtual environment...
    python -m venv venv
)

:: Activate
call venv\Scripts\activate.bat

:: Install dependencies
echo [INFO] Installing dependencies...
pip install -r requirements.txt -q

:: Create .env if missing
if not exist ".env" (
    copy "..\\.env.example" ".env" >nul 2>&1
    echo [WARN] Created .env from template. Edit it to add your API keys.
)

echo.
echo [OK] Starting server → http://localhost:8000
echo [OK] API Docs        → http://localhost:8000/docs
echo.

python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload

pause
