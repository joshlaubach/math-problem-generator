# Monorepo Structure Guide

## Overview

The `Math Problem Generator` folder is now organized as a **monorepo** with a clear separation between backend and frontend. This structure is ideal for GitHub repository initialization and deployment.

## Directory Layout

```
Math Problem Generator/
│
├── backend/
│   ├── api.py                    # FastAPI main application
│   ├── models.py                 # Domain models
│   ├── db_models.py              # SQLAlchemy ORM models
│   ├── db_session.py             # Database connection management
│   ├── config.py                 # Configuration management
│   ├── repositories.py           # Data access layer
│   ├── llm_factory.py            # LLM provider factory
│   ├── llm_interfaces.py         # LLM interface definitions
│   ├── llm_openai_client.py      # OpenAI implementation
│   ├── adaptive.py               # Adaptive difficulty logic
│   ├── cli.py                    # Command-line interface
│   ├── tracking.py               # User tracking and stats
│   ├── taxonomy.py               # Problem taxonomy
│   ├── word_problem.py           # Word problem handling
│   ├── storage.py                # Storage abstraction
│   ├── generators/               # Problem generation engines
│   │   ├── __init__.py
│   │   ├── base_generator.py
│   │   ├── linear_generator.py
│   │   └── inequality_generator.py
│   ├── tests/                    # Test suite (264 tests)
│   │   ├── test_generators.py
│   │   ├── test_api.py
│   │   ├── test_db.py
│   │   ├── test_llm.py
│   │   └── ... (more test files)
│   ├── requirements.txt          # Python dependencies
│   ├── README.md                 # Backend documentation
│   ├── DESIGN.md                 # System design
│   └── ... (other docs and files)
│
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   │   ├── client.ts         # Typed API client
│   │   │   └── types.ts          # TypeScript interfaces
│   │   ├── components/           # React components
│   │   │   ├── Header.tsx
│   │   │   ├── Header.css
│   │   │   ├── TopicSelector.tsx
│   │   │   ├── TopicSelector.css
│   │   │   ├── DifficultySelector.tsx
│   │   │   ├── ProblemView.tsx
│   │   │   ├── ProblemView.css
│   │   │   └── MathText.tsx
│   │   ├── pages/                # Page-level components
│   │   │   ├── StudentDashboard.tsx
│   │   │   ├── StudentDashboard.css
│   │   │   ├── TeacherDashboard.tsx
│   │   │   └── TeacherDashboard.css
│   │   ├── hooks/                # Custom React hooks
│   │   │   └── useUserIdentity.ts
│   │   ├── App.tsx               # Main app component
│   │   ├── App.css               # Global styles
│   │   ├── main.tsx              # React entry point
│   │   └── config.ts             # Configuration
│   ├── index.html                # HTML entry point
│   ├── package.json              # npm dependencies
│   ├── vite.config.ts            # Vite build config
│   ├── tsconfig.json             # TypeScript config
│   ├── tsconfig.node.json        # TypeScript (build) config
│   ├── .env.local                # Environment variables
│   ├── .gitignore                # Frontend-specific ignores
│   ├── README.md                 # Frontend documentation
│   ├── QUICKSTART.md             # Quick start guide
│   └── src/                      # React source files
│
├── README.md                     # Monorepo main documentation
├── package.json                  # Monorepo scripts
├── .gitignore                    # Global git ignores
├── ARCHITECTURE_DIAGRAMS.md      # System architecture (8 diagrams)
├── COMPLETE_SYSTEM_OVERVIEW.md   # Full project overview
├── PHASE6_FRONTEND_SUMMARY.md    # Frontend implementation details
└── PHASE6_IMPLEMENTATION_CHECKLIST.md # Feature checklist
```

## Key Points

### Backend Structure
- **Self-contained Python project** with all dependencies in `requirements.txt`
- **Tests in `tests/` folder** with 264 passing tests
- **No Python virtual environment** stored in repo (.venv goes in .gitignore)
- **FastAPI application** in `api.py` as entry point

### Frontend Structure
- **Self-contained Node.js project** with all dependencies in `package.json`
- **Vite-based build** with TypeScript strict mode
- **Source code in `src/`** following React best practices
- **No node_modules** in repo (.gitignore handles this)

### Monorepo Root
- **Single README.md** describes the entire project
- **Single .gitignore** covers Python, Node.js, and IDE files
- **Single package.json** provides convenient scripts for full-stack development
- **Documentation files** at root level for easy access

## Git Repository Setup

This folder is ready to become a GitHub repository:

```bash
cd "Math Problem Generator"
git init
git add .
git commit -m "Initial commit: Full-stack math problem generator with React frontend and FastAPI backend"
git remote add origin https://github.com/yourusername/math-problem-generator.git
git branch -M main
git push -u origin main
```

## Development Workflow

### Option 1: Separate Terminals (Recommended)

**Terminal 1 - Backend:**
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt
python -m uvicorn api:app --reload --port 8000
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm install
npm run dev
```

### Option 2: Using Root Scripts

From root directory:
```bash
# Install both
cd backend && pip install -r requirements.txt
cd ../frontend && npm install
cd ..

# Run both (with npm concurrently)
npm run dev
```

## Environment Variables

### Backend (.env in backend/)
```
DATABASE_URL=postgresql://user:password@localhost/mpg_db
OPENAI_API_KEY=sk-xxxxxxxxxxxx
TEACHER_ACCESS_CODE=TEACHER123
```

### Frontend (.env.local in frontend/)
```
VITE_API_BASE_URL=http://localhost:8000
VITE_TEACHER_ACCESS_CODE=TEACHER123
```

## Testing

```bash
# Backend: Run all 264 tests
cd backend
pytest tests/ -v

# Backend: With coverage
pytest tests/ -v --cov

# Frontend: Coming Phase 7
cd frontend
npm run test
```

## Building for Production

```bash
# Backend: Already production-ready
cd backend
# Set DATABASE_URL to production database
python -m uvicorn api:app --host 0.0.0.0 --port 8000

# Frontend: Build static assets
cd frontend
npm run build
# Output: dist/ folder (ready for static hosting)
```

## Deployment Options

1. **Traditional Hosting**
   - Backend: Deploy to Heroku, Railway, or VPS
   - Frontend: Deploy to Vercel, Netlify, or static hosting

2. **Docker**
   - Create Dockerfile for backend (Python)
   - Create Dockerfile for frontend (Node)
   - Use docker-compose for local development

3. **Cloud Platforms**
   - AWS (Lambda + CloudFront, or EC2 + S3)
   - Google Cloud (App Engine + Cloud Storage)
   - Azure (App Service + Static Web Apps)

## CI/CD Ready

The structure supports standard CI/CD workflows:

```yaml
# GitHub Actions example
- Run backend tests: cd backend && pytest tests/ -v
- Build frontend: cd frontend && npm run build
- Deploy backend to cloud
- Deploy frontend to CDN
```

## Documentation

All documentation is organized by scope:

| Document | Scope | Content |
|----------|-------|---------|
| `README.md` | Project | Overview, setup, features |
| `backend/README.md` | Backend | API documentation, DB setup |
| `frontend/README.md` | Frontend | Component docs, styling system |
| `ARCHITECTURE_DIAGRAMS.md` | System | 8 detailed ASCII diagrams |
| `COMPLETE_SYSTEM_OVERVIEW.md` | Project | Deployment, workflow, roadmap |
| `PHASE6_FRONTEND_SUMMARY.md` | Frontend | Implementation details |

## Next Steps

1. **Initialize Git Repository**
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   ```

2. **Install Dependencies**
   ```bash
   cd backend && pip install -r requirements.txt
   cd ../frontend && npm install
   ```

3. **Run Tests**
   ```bash
   cd backend && pytest tests/ -v
   ```

4. **Start Development**
   ```bash
   # Backend (Terminal 1)
   cd backend && python -m uvicorn api:app --reload --port 8000
   
   # Frontend (Terminal 2)
   cd frontend && npm run dev
   ```

5. **Access Application**
   - Frontend: http://localhost:5173
   - API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

---

**Last Updated**: December 9, 2025  
**Status**: Ready for GitHub ✅
