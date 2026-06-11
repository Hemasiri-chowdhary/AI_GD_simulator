@echo off
echo ========================================
echo    AI-GD-Pro Backend Startup
echo ========================================
echo.

cd /d %~dp0

echo Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    pause
    exit /b 1
)

echo.
echo Creating virtual environment...
if not exist "venv" (
    python -m venv venv
)

echo Activating virtual environment...
call venv\Scripts\activate.bat

echo.
echo Installing dependencies...
pip install -r requirements.txt --quiet

echo.
echo Creating .env file if not exists...
if not exist ".env" (
    copy .env.example .env
)

echo.
echo ========================================
echo    Starting FastAPI Server
echo    URL: http://127.0.0.1:8000
echo    WebSocket: ws://127.0.0.1:8000/ws/chat
echo ========================================
echo.

python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
