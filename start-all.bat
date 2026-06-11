@echo off
echo ========================================
echo    AI-GD-Pro - Full Stack Startup
echo ========================================
echo.
echo This script will start both backend and frontend.
echo.
echo Prerequisites:
echo   1. Python 3.10+ installed
echo   2. Node.js 18+ installed
echo   3. Ollama running with llama3 model
echo.
echo ========================================
echo.

echo Starting Backend Server...
start "AI-GD-Pro Backend" cmd /k "cd /d %~dp0backend && start.bat"

echo Waiting for backend to initialize...
timeout /t 5 /nobreak >nul

echo Starting Frontend Server...
start "AI-GD-Pro Frontend" cmd /k "cd /d %~dp0frontend && start.bat"

echo.
echo ========================================
echo    Servers Starting...
echo.
echo    Backend: http://127.0.0.1:8000
echo    Frontend: http://localhost:3000
echo.
echo    Press any key to exit this window.
echo ========================================
pause >nul
