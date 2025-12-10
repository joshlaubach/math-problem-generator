# Math Problem Generator - Startup Script
# Starts both backend and frontend servers

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  Math Problem Generator - Startup Script" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# Check if backend/.venv exists
$backend_path = ".\backend"
$venv_path = "$backend_path\.venv"

if (-not (Test-Path $venv_path)) {
    Write-Host "⚙️  Creating Python virtual environment..." -ForegroundColor Yellow
    python -m venv $venv_path
}

# Install/update dependencies
Write-Host "⚙️  Installing Python dependencies..." -ForegroundColor Yellow
& "$venv_path\Scripts\python.exe" -m pip install -q fastapi uvicorn sympy pydantic python-jose passlib sqlalchemy psycopg2-binary aiofiles requests email-validator pytest httpx pytest-asyncio 2>$null

Write-Host ""
Write-Host "🚀 Starting Backend Server..." -ForegroundColor Green
Write-Host "   URL: http://localhost:8000" -ForegroundColor Cyan
Write-Host "   API Docs: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "   Press CTRL+C to stop" -ForegroundColor Yellow
Write-Host ""

# Start backend
Push-Location $backend_path
& ".\.venv\Scripts\python.exe" -m uvicorn api:app --reload --port 8000
Pop-Location
