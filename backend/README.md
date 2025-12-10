# Math Problem Generator

A solution-first problem generation system for educational mathematics content. This initial version focuses on generating one-variable linear equations with automatic step-by-step solutions.

## Architecture

### Modules

**`taxonomy.py`**  
Defines the hierarchical course structure: `Course` → `Unit` → `Topic`. Provides `get_algebra1_course()` to instantiate the first slice covering Algebra I Linear Equations and Inequalities.

**`models.py`**  
Core dataclasses:
- `CalculatorMode`: Literal type for "none", "scientific", "graphing"
- `SolutionStep`: Single step in a solution (index, description LaTeX, expression LaTeX)
- `Solution`: Complete solution with steps, full LaTeX, final answer, and SymPy verification
- `Problem`: Full problem definition with course/unit/topic IDs, difficulty, prompt LaTeX, and metadata

**`generator_linear.py`**  
Generator implementation for one-variable linear equations:
- `generate_linear_equation_problem(difficulty, calculator_mode)`: Main entry point
- Difficulty levels 1–4 with increasing complexity
- Solution-first approach: target solution → equation construction → SymPy verification → step generation
- Pure functions for equation building, verification, and step construction

**`demo_linear.py`**  
Simple CLI demo that generates and displays problems for all difficulty levels with complete LaTeX formatting.

## Usage

### Basic Generation

```python
from generator_linear import generate_linear_equation_problem

# Generate a difficulty 2 problem
problem = generate_linear_equation_problem(difficulty=2)

# Access problem details
print(problem.prompt_latex)           # "Solve for $x$: ..."
print(problem.final_answer)           # The solution value

# Access solution from metadata
solution = problem.metadata["solution"]
print(solution.final_answer_latex)    # LaTeX for final answer
print(solution.full_solution_latex)   # Complete step-by-step solution
print(solution.sympy_verified)        # True/False verification status
```

### Run Demo

```bash
python demo_linear.py
```

This generates four sample problems (one per difficulty level) and displays their complete solutions.

## Problem Difficulty Levels

### Difficulty 1: Simple Addition/Subtraction
**Form:** `x + b = c` or `x - b = c`  
**Example:** `x + 5 = 12`  
**Steps:** Subtract constant, simplify

### Difficulty 2: One-Step Multiplication/Division
**Form:** `a·x + b = c`  
**Example:** `3x - 2 = 10`  
**Steps:** Subtract constant, divide by coefficient, simplify

### Difficulty 3: Variables on Both Sides
**Form:** `a·x + b = c·x + d`  
**Example:** `2x + 7 = 5x - 2`  
**Steps:** Collect variables, collect constants, divide, simplify

### Difficulty 4: Fractional Coefficients
**Form:** `(p/q)·x + b = (r/s)·x + d`  
**Example:** `(1/2)x + 3 = (3/4)x - 1`  
**Steps:** Same as difficulty 3 but with rational arithmetic

## Data Flow

```
Target Solution x₀
    ↓
Build Equation (a·x + b = c·x + d)
    ↓
Verify with SymPy (solve & check)
    ↓
Generate Solution Steps
    ↓
Create LaTeX Representations
    ↓
Assemble Problem & Solution Objects
```

## Technical Details

- **Language:** Python 3.10+
- **Type Hints:** Full coverage on all public functions
- **Math Engine:** SymPy for symbolic computation and verification
- **LaTeX Generation:** Automatic via SymPy's `latex()` function
- **Verification:** Each generated equation is verified to have exactly one integer solution

## Authentication & Authorization (Phase 9–10)

The system supports two authentication mechanisms:

### 1. JWT-Based Authentication (Recommended)

Register a new user and receive a JWT token:

```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "student@school.edu",
    "password": "SecurePassword123",
    "role": "student",
    "display_name": "John Doe"
  }'

# Response includes access_token
```

Use the token in subsequent requests:

```bash
curl -X GET http://localhost:8000/me/stats/alg1_linear_solve_one_var \
  -H "Authorization: Bearer <access_token>"
```

**Token Details:**
- Algorithm: HS256
- Default expiry: 60 minutes
- Contains: user_id, role, issued_at, expiry

### 2. Legacy API Key (Backward Compatibility)

Existing teacher/admin integrations can continue using API keys:

```bash
curl -X GET http://localhost:8000/teacher/topic_stats?topic_id=alg1_linear_solve_one_var \
  -H "X-API-Key: your_teacher_api_key"
```

Both mechanisms work in parallel. **Migration to JWT is optional but recommended.**

### Roles

- **student**: Can submit attempts, view personal stats/recommendations
- **teacher**: Can create assignments, view aggregated analytics, access all student features
- **admin**: Can access all teacher features and future admin operations

### Endpoints

**Authentication:**
- `POST /auth/register` - Register new user
- `POST /auth/login` - Login and get JWT token

**Authenticated Student:**
- `GET /me/stats/{topic_id}` - Personal topic statistics
- `GET /me/recommend/{topic_id}` - Recommended difficulty
- `POST /attempt` - Submit attempt (with optional JWT)

**Teacher/Admin Only:**
- `GET /teacher/topic_stats` - Aggregated topic statistics
- `GET /teacher/user_overview` - User statistics across topics
- `GET /teacher/recent_attempts` - Recent attempts across users
- `POST /teacher/assignments` - Create assignment
- `GET /teacher/assignments/{id}/stats` - Assignment analytics

See [PHASE_10.md](../PHASE_10.md) for detailed authentication documentation.

## Technical Details

- **Language:** Python 3.10+
- **Type Hints:** Full coverage on all public functions
- **Math Engine:** SymPy for symbolic computation and verification
- **LaTeX Generation:** Automatic via SymPy's `latex()` function
- **Verification:** Each generated equation is verified to have exactly one integer solution
- **Framework:** FastAPI with Pydantic validation
- **ORM:** SQLAlchemy for database models
- **Password Security:** Bcrypt hashing via passlib

## Future Extensions

- Additional equation types (quadratic, rational, etc.)
- More difficulty ranges within each topic
- Different answer types (expressions, intervals, etc.)
- Student attempt tracking and feedback
- Performance metrics and adaptive difficulty
