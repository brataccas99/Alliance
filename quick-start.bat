@echo off
REM Quick Start Script for Alliance PNRR Futura Dashboard (Windows)

echo ======================================
echo Alliance PNRR Futura Dashboard
echo Quick Start Script (Windows)
echo ======================================
echo.

REM Check for Docker
where docker >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Error: Docker is not installed. Please install Docker Desktop first.
    exit /b 1
)

REM Check for Node.js
where node >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Error: Node.js is not installed. Please install Node.js first.
    exit /b 1
)

echo All requirements met!
echo.

REM Create .env file if it doesn't exist
if not exist .env (
    echo Creating .env file from template...
    copy .env.example .env
    echo .env file created! Please review and update if needed.
) else (
    echo .env file already exists, skipping...
)
echo.

REM Install frontend dependencies
echo Installing frontend dependencies...
cd frontend
call npm install
cd ..
echo Frontend dependencies installed!
echo.

REM Build frontend
echo Building frontend...
cd frontend
call npm run build
cd ..
echo Frontend built successfully!
echo.

REM Start Docker services
echo Starting Docker services...
docker-compose up -d
echo Services started!
echo.

REM Wait for services
echo Waiting for services to be ready...
timeout /t 10 /nobreak >nul
echo Services should be ready!
echo.

REM Display status
echo ======================================
echo Alliance Dashboard is running!
echo ======================================
echo.
echo Application: http://localhost:5000
echo MongoDB:     localhost:27017
echo.
echo Useful commands:
echo   docker-compose logs -f backend   # View backend logs
echo   docker-compose logs -f mongodb   # View database logs
echo   docker-compose down              # Stop all services
echo   docker-compose ps                # Check service status
echo.

pause
