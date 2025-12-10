# 🚀 Quick Start Guide

## One-Command Startup

### Windows (PowerShell)
```powershell
cd "C:\Users\joshu\Documents\Projects\Math Problem Generator"
.\START.ps1
```

The backend will start on `http://localhost:8000`

## What's Running

### Backend API
- **URL**: http://localhost:8000
- **Interactive API Docs**: http://localhost:8000/docs
- **Alternative Docs**: http://localhost:8000/redoc

## Test the API

Once running, you can:

1. **Open API Docs** in browser: http://localhost:8000/docs
2. **Try endpoints**:
   - `GET /topics` - List all math topics
   - `POST /generate` - Generate a math problem
   - `GET /health` - Check API status

## Run Tests

From the backend directory:
```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest tests/ -v
```

Expected: **402 tests passing** ✅

## Project Structure

```
Math Problem Generator/
├── backend/              # FastAPI Python backend
│   ├── api.py           # Main API server
│   ├── tests/           # 402 test cases
│   ├── generators/      # Problem generation engines
│   └── .venv/           # Python virtual environment
│
├── frontend/            # React frontend (optional)
└── START.ps1           # Startup script (this file)
```

## Features

- ✅ 402 passing unit tests
- ✅ FastAPI with full OpenAPI docs
- ✅ Problem generation with solutions
- ✅ Student attempt tracking
- ✅ Teacher analytics dashboard
- ✅ Authentication & role-based access
- ✅ Adaptive difficulty recommendations

## Troubleshooting

### Python not found
Make sure Python 3.9+ is installed and in PATH:
```powershell
python --version
```

### Port 8000 already in use
Change the port in START.ps1:
```powershell
# Change this line:
& ".\.venv\Scripts\python.exe" -m uvicorn api:app --reload --port 8000

# To:
& ".\.venv\Scripts\python.exe" -m uvicorn api:app --reload --port 8001
```

### Still having issues?
Check manual startup:
```powershell
cd backend
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn api:app --reload --port 8000
```
