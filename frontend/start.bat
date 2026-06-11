@echo off
echo ========================================
echo    AI-GD-Pro Frontend Startup
echo ========================================
echo.

cd /d %~dp0

echo Checking Node.js installation...
node --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Node.js is not installed or not in PATH
    pause
    exit /b 1
)

echo.
echo Installing dependencies...
if not exist "node_modules" (
    call npm install
) else (
    echo Dependencies already installed.
)

echo.
echo ========================================
echo    Starting Next.js Development Server
echo    URL: http://localhost:3000
echo ========================================
echo.

npm run dev
