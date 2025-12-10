# Math Problem Generator - Full Stack Application

[![Tests: 402 passing](https://img.shields.io/badge/tests-402%20passing-brightgreen)](backend/tests)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue)](https://www.python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-009485)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18.2+-61dafb)](https://react.dev)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

> AI-powered math problem generation platform with adaptive difficulty, teacher analytics, and student progress tracking.

## ✨ Features

### 🎓 Student Features
- **Interactive Problem Solving** - Browse topics, generate problems, solve with AI-powered hints
- **Adaptive Difficulty** - System recommends next difficulty based on your performance
- **Progress Tracking** - View detailed stats: success rate, average time, difficulty progression
- **AI Hints & Solutions** - Get contextual hints or step-by-step solutions on demand

### 👨‍🏫 Teacher Features
- **Student Analytics** - View individual student performance by topic with heatmaps
- **Assignment Management** - Create targeted assignments with pre-generated problem sets
- **Performance Insights** - Track attempts, success rates, and learning gaps
- **Concept Mapping** - See which concepts students struggle with most

### ⚙️ Backend Capabilities
- **402 Unit Tests** - Comprehensive test coverage with pytest
- **Problem Generators** - Linear equations, inequalities, word problems with SymPy verification
- **LLM Integration** - OpenAI API for intelligent hints and solutions
- **Database Ready** - PostgreSQL + SQLAlchemy ORM for production scale
- **Role-Based Auth** - JWT tokens with student/teacher/admin roles
- **Concept Tracking** - 51 Algebra 1 concepts with prerequisite DAG

## 🚀 Quick Start

### 1️⃣ Start Backend (5 minutes)

```powershell
# Windows - From project root
.\START.ps1

# OR manually:
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install fastapi uvicorn sympy pydantic python-jose passlib sqlalchemy email-validator
python -m uvicorn api:app --reload --port 8000
```

### 2️⃣ Access API

- **Interactive Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **API Base**: http://localhost:8000

### 3️⃣ Run Tests

```bash
cd backend
python -m pytest tests/ -v
# Expected: 402 passed ✅
```

## 📁 Project Structure

```
Math Problem Generator/
├── backend/                      # FastAPI Python backend (production-ready)
│   ├── api.py                   # Main FastAPI app + 40+ endpoints
│   ├── generators/              # Problem generation engines
│   ├── tests/                   # 402 test cases (100% passing)
│   ├── auth_*.py                # Authentication & authorization
│   ├── repositories_*.py        # Data access layer (JSONL/PostgreSQL)
│   ├── concepts.py              # Concept DAG with prerequisites
│   ├── alg1_concepts.py         # 51 Algebra 1 concepts
│   └── requirements.txt         # Python dependencies
│
├── frontend/                     # React + TypeScript frontend (ready for design)
│   ├── src/
│   │   ├── components/          # Reusable React components
│   │   ├── pages/               # StudentDashboard, TeacherDashboard
│   │   ├── api/                 # HTTP client layer
│   │   └── App.tsx              # Main app component
│   ├── package.json
│   ├── vite.config.ts
│   └── tsconfig.json
│
├── data/                        # Sample datasets
├── Dockerfile                   # Docker configuration
├── START.ps1                    # One-command startup script
├── STARTUP_GUIDE.md            # Setup instructions
└── README.md                    # This file
```

## 🔧 Technology Stack

### Backend
- **Framework**: FastAPI 0.104+ (Python 3.9+)
- **Database**: PostgreSQL + SQLAlchemy ORM
- **LLM**: OpenAI API (gpt-4-turbo-preview)
- **Testing**: pytest (402 tests, 100% passing)
- **Async**: asyncio + uvicorn
- **Math**: SymPy for equation verification

### Frontend
- **Framework**: React 18.2+ with TypeScript
- **Build**: Vite 5.0
- **HTTP**: Axios with centralized API client
- **Testing**: Vitest + React Testing Library
- **Styling**: CSS with BEM methodology

## 📊 Project Status

| Component | Status | Tests | Lines |
|-----------|--------|-------|-------|
| Problem Generators | ✅ Complete | 82 | 2000+ |
| API Backend | ✅ Complete | 154 | 1800+ |
| Database Layer | ✅ Complete | 28 | 400+ |
| LLM Integration | ✅ Complete | 28 | 300+ |
| Authentication | ✅ Complete | 110 | 600+ |
| Assignments | ✅ Complete | 27 | 500+ |
| **Total Backend** | ✅ **Complete** | **402** | **5600+** |
| Frontend | ✅ Complete | - | 1400+ |

**Production Ready**: Yes ✅

## 🔌 API Endpoints

### Public Endpoints
```
GET  /topics                          # List all topics
POST /generate?topic_id=...           # Generate a problem
POST /attempt                         # Submit answer
POST /hint?problem_id=...             # Get AI hint
GET  /health                          # Health check
```

### Student Endpoints (requires JWT)
```
GET  /me                              # Get current user
GET  /me/stats?topic_id=...          # Get performance stats
GET  /me/recommend?topic_id=...      # Get difficulty recommendation
```

### Teacher Endpoints (requires API key or JWT with teacher role)
```
GET  /teacher/students              # List all students
GET  /teacher/topics/{topicId}/stats  # Topic-wide analytics
POST /teacher/assignments            # Create assignment
GET  /teacher/assignments/{id}        # Get assignment
```

### Auth Endpoints
```
POST /auth/register                  # Register new user
POST /auth/login                     # Login with email/password
POST /auth/refresh                   # Refresh JWT token
```

## 🧪 Testing

### Backend Tests (402 total)
```bash
cd backend

# Run all tests
python -m pytest tests/ -v

# Run specific category
python -m pytest tests/test_api.py -v
python -m pytest tests/test_auth_*.py -v
python -m pytest tests/test_assignments_api.py -v

# With coverage
python -m pytest tests/ --cov=. --cov-report=html
```

### Frontend Tests
```bash
cd frontend
npm test                    # Run tests
npm run test:coverage      # Coverage report
```

## 🌐 Deployment

### Docker (Recommended)
```bash
docker build -t math-problem-generator .
docker run -p 8000:8000 -e OPENAI_API_KEY=... math-problem-generator
```

### Manual Deployment
```bash
# Backend
cd backend
pip install -r requirements.txt
python -m uvicorn api:app --host 0.0.0.0 --port 8000

# Frontend (optional)
cd frontend
npm install && npm run build
# Deploy dist/ to static host
```

### Environment Variables

**Backend** (`backend/.env`)
```
DATABASE_URL=postgresql://user:password@localhost/mpg
OPENAI_API_KEY=sk-...
TEACHER_API_KEY=your-teacher-key
ADMIN_API_KEY=your-admin-key
JWT_SECRET=your-secret-key
```

**Frontend** (`frontend/.env.local`)
```
VITE_API_BASE_URL=http://localhost:8000
```

## 🎨 Frontend Design

The frontend codebase is structured and ready for design improvements:

- **Components**: Modular, functional React components with TypeScript
- **Pages**: StudentDashboard and TeacherDashboard ready for UI enhancements
- **API Layer**: Centralized HTTP client with proper error handling
- **Testing**: Comprehensive test suite with mock data

**Recommendations for UI/UX enhancement**:
1. Use Lovable AI (https://lovable.ai) - Upload GitHub repo, get beautiful UI
2. Apply Tailwind CSS + Shadcn/ui for modern components
3. Implement responsive mobile design
4. Add dark mode support

## 📚 Documentation

- **[STARTUP_GUIDE.md](STARTUP_GUIDE.md)** - Quick start instructions
- **[MONOREPO_STRUCTURE.md](MONOREPO_STRUCTURE.md)** - Project organization
- **[backend/README.md](backend/README.md)** - Backend documentation
- **[frontend/README.md](frontend/README.md)** - Frontend documentation

## 🤝 Contributing

Contributions welcome! Areas to enhance:

- **Frontend Design** - Modern UI/UX improvements
- **Additional Problem Types** - Geometry, calculus, statistics
- **Mobile App** - React Native version
- **Internationalization** - Multi-language support
- **Accessibility** - WCAG compliance

## 📝 License

MIT License - See [LICENSE](LICENSE) file

## 👤 Author

Created December 2024

## 🙏 Acknowledgments

- FastAPI for the excellent web framework
- React for the UI library
- OpenAI for the LLM API
- SymPy for symbolic mathematics
- All open-source contributors

---

**Get Started**: Run `.\START.ps1` to launch the backend in seconds! 🚀

**Have questions?** Check the [STARTUP_GUIDE.md](STARTUP_GUIDE.md) or review the API docs at http://localhost:8000/docs
