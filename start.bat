@echo off
REM Domain Enrichment SaaS - Quick Start Script (Windows)

echo Starting Domain Enrichment SaaS...
echo.

REM Check if Docker is available
docker --version >nul 2>&1
if %errorlevel% equ 0 (
    echo Docker detected
    echo Starting with Docker Compose...
    docker-compose up -d
    echo.
    echo Application started!
    echo Open your browser: http://localhost:8000
    echo.
    echo View logs: docker-compose logs -f
    echo Stop: docker-compose down
) else (
    echo Docker not found. Starting with Python...
    echo.

    REM Check if virtual environment exists
    if not exist "venv" (
        echo Creating virtual environment...
        python -m venv venv
    )

    REM Activate virtual environment
    echo Activating virtual environment...
    call venv\Scripts\activate.bat

    REM Install dependencies
    echo Installing dependencies...
    pip install -q -r requirements.txt

    REM Start the application
    echo.
    echo Starting application...
    python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
)
