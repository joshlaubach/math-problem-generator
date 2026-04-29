# Curriculum Database Schema

## Overview

The curriculum is now stored in database tables organized hierarchically:

```
Education Level (High School, College/University, Test Prep)
  ├── Course (e.g., Algebra 1, Calculus I, SAT Math)
  │   ├── Unit (e.g., "Linear Equations and Inequalities")
  │   │   ├── Topic (e.g., "Solving one-variable linear equations")
  │   │   │   └── Concept (e.g., "One-step equations with integers")
```

## Database Tables

### education_levels
Top-level categorization of curriculum.

| Column | Type | Description |
|--------|------|-------------|
| id | String(50) PK | `high_school`, `college_university`, `test_prep` |
| name | String(100) | Display name |
| description | Text | Optional description |
| display_order | Integer | Sort order |
| is_active | Boolean | Enable/disable |
| created_at | DateTime | Creation timestamp |
| updated_at | DateTime | Last update |

**Indexes:**
- `display_order`
- `is_active`

### courses
Courses within an education level.

| Column | Type | Description |
|--------|------|-------------|
| id | String(100) PK | `algebra_1`, `calculus_1`, `sat_math` |
| name | String(200) | Display name |
| description | Text | Optional description |
| education_level_id | String(50) FK | References `education_levels.id` |
| display_order | Integer | Sort order within level |
| is_active | Boolean | Enable/disable |
| code | String(20) | Course code (e.g., `ALG1`, `CALC1`) |
| credits | Float | College credit hours (optional) |
| prerequisites_json | Text | JSON list of prerequisite course IDs |
| created_at | DateTime | Creation timestamp |
| updated_at | DateTime | Last update |

**Indexes:**
- `(education_level_id, display_order)`
- `(education_level_id, is_active)`

### units
Units within a course.

| Column | Type | Description |
|--------|------|-------------|
| id | String(100) PK | `alg1_unit_linear_equations` |
| name | String(200) | Display name |
| description | Text | Optional description |
| course_id | String(100) FK | References `courses.id` |
| display_order | Integer | Sort order within course |
| is_active | Boolean | Enable/disable |
| created_at | DateTime | Creation timestamp |
| updated_at | DateTime | Last update |

**Indexes:**
- `(course_id, display_order)`
- `(course_id, is_active)`

### topics
Topics within a unit (what students practice).

| Column | Type | Description |
|--------|------|-------------|
| id | String(100) PK | `alg1_linear_solve_one_var` |
| name | String(200) | Display name |
| description | Text | Optional description |
| unit_id | String(100) FK | References `units.id` |
| course_id | String(100) FK | References `courses.id` |
| display_order | Integer | Sort order within unit |
| is_active | Boolean | Enable/disable |
| prerequisites_json | Text | JSON list of prerequisite topic IDs |
| difficulty_min | Integer | Minimum difficulty (1-10) |
| difficulty_max | Integer | Maximum difficulty (1-10) |
| created_at | DateTime | Creation timestamp |
| updated_at | DateTime | Last update |

**Indexes:**
- `(unit_id, display_order)`
- `(unit_id, is_active)`
- `(course_id, id)`

### concepts
Granular learning objectives forming a prerequisite DAG.

| Column | Type | Description |
|--------|------|-------------|
| id | String(150) PK | `alg1.linear_eq.one_step_int` |
| name | String(200) | Display name |
| description | Text | What students learn |
| topic_id | String(100) FK | References `topics.id` |
| unit_id | String(100) FK | References `units.id` |
| course_id | String(100) FK | References `courses.id` |
| kind | String(50) | `skill`, `definition`, `strategy`, `representation` |
| difficulty_min | Integer | Minimum difficulty (1-6) |
| difficulty_max | Integer | Maximum difficulty (1-6) |
| prerequisites_json | Text | JSON list of prerequisite concept IDs |
| examples_latex_json | Text | JSON list of LaTeX examples |
| tags_json | Text | JSON list of searchable tags |
| is_active | Boolean | Enable/disable |
| version | String(20) | Concept version (e.g., `v1`) |
| created_at | DateTime | Creation timestamp |
| updated_at | DateTime | Last update |

**Indexes:**
- `(topic_id, id)`
- `(unit_id, id)`
- `(course_id, id)`
- `is_active`

## Migration

### Running the Migration

```bash
cd backend
python migrate_curriculum_to_db.py
```

This will:
1. Create all curriculum tables
2. Populate 3 education levels
3. Create 15 courses across the levels
4. Migrate all concepts from the in-memory registry to the database

### Migration Output

```
Starting curriculum migration to database...
============================================================

Creating database tables...
✓ Tables created

Creating education levels...
✓ Created education level: High School
✓ Created education level: College/University
✓ Created education level: Test Prep

Creating courses...
✓ Created course: Pre-Algebra (high_school)
✓ Created course: Algebra 1 (high_school)
✓ Created course: Geometry (high_school)
✓ Created course: Algebra 2 (high_school)
✓ Created course: Pre-Calculus (high_school)
✓ Created course: Calculus I (college_university)
✓ Created course: Calculus II (college_university)
✓ Created course: Calculus III (Multivariable Calculus) (college_university)
✓ Created course: Linear Algebra (college_university)
✓ Created course: Differential Equations (college_university)
✓ Created course: Probability and Statistics (college_university)
✓ Created course: SAT Math (test_prep)
✓ Created course: AP Calculus AB (test_prep)
✓ Created course: AP Calculus BC (test_prep)
✓ Created course: Math Contest Problems (test_prep)

Migrating concepts...
✓ Migrated XXX concepts to database

============================================================
MIGRATION VERIFICATION
============================================================
Education Levels: 3
Courses: 15
  - High School: 5 courses
  - College/University: 6 courses
  - Test Prep: 4 courses
Units: X
Topics: X
Concepts: XXX
```

## API Endpoints

### Education Levels

**GET /curriculum/education-levels**
- Returns all education levels ordered by display_order
- Response: `list[EducationLevelResponse]`

### Courses

**GET /curriculum/courses**
- Query params: `education_level_id` (optional)
- Returns courses filtered by education level
- Response: `list[CourseResponse]`

**GET /curriculum/courses/{course_id}**
- Returns single course details
- Response: `CourseResponse`

### Units

**GET /curriculum/units**
- Query params: `course_id` (optional)
- Returns units filtered by course
- Response: `list[UnitResponse]`

### Topics

**GET /curriculum/topics**
- Query params: `course_id`, `unit_id` (optional)
- Returns topics filtered by course/unit
- Response: `list[TopicResponse]`

### Concepts

**GET /curriculum/concepts**
- Query params: `course_id`, `unit_id`, `topic_id` (optional)
- Returns concepts filtered by course/unit/topic
- Response: `list[ConceptDbResponse]`

## Course Structure

### High School (5 courses)

1. **Pre-Algebra** (`pre_algebra`)
   - Integers, fractions, decimals, ratios, basic equations

2. **Algebra 1** (`algebra_1`)
   - Linear equations, inequalities, systems, exponents, polynomials
   - Prerequisites: Pre-Algebra

3. **Geometry** (`geometry`)
   - Plane/solid geometry, proofs, congruence, similarity, area, volume
   - Prerequisites: Algebra 1

4. **Algebra 2** (`algebra_2`)
   - Quadratics, exponentials, logarithms, rational functions, sequences
   - Prerequisites: Algebra 1

5. **Pre-Calculus** (`precalculus`)
   - Trigonometry, polar coordinates, complex numbers, limits
   - Prerequisites: Algebra 2

### College/University (6 courses)

1. **Calculus I** (`calculus_1`) - 4 credits
   - Limits, derivatives, applications, integration
   - Prerequisites: Pre-Calculus

2. **Calculus II** (`calculus_2`) - 4 credits
   - Integration techniques, sequences, series, parametric equations
   - Prerequisites: Calculus I

3. **Calculus III** (`calculus_3`) - 4 credits
   - Multivariable calculus, vectors, partial derivatives, multiple integrals
   - Prerequisites: Calculus II

4. **Linear Algebra** (`linear_algebra`) - 3 credits
   - Vector spaces, matrices, transformations, eigenvalues
   - Prerequisites: Calculus I

5. **Differential Equations** (`differential_equations`) - 3 credits
   - ODEs, systems, Laplace transforms, applications
   - Prerequisites: Calculus II, Linear Algebra

6. **Probability and Statistics** (`probability_statistics`) - 3 credits
   - Probability theory, distributions, hypothesis testing, regression
   - Prerequisites: Calculus I

### Test Prep (4 courses)

1. **SAT Math** (`sat_math`)
   - SAT prep covering algebra, problem solving, data analysis

2. **AP Calculus AB** (`ap_calculus_ab`)
   - AP exam prep: derivatives, integrals, applications
   - Prerequisites: Pre-Calculus

3. **AP Calculus BC** (`ap_calculus_bc`)
   - AP exam prep: all AB plus series, parametric
   - Prerequisites: AP Calculus AB

4. **Math Contest Problems** (`contest_math`)
   - Competition math: AMC, AIME, USAMO, proofs

## Benefits of Database Schema

### Before (Code-defined)
- ✅ Fast in-memory access
- ✅ Version controlled
- ❌ Can't modify at runtime
- ❌ No admin interface possible
- ❌ No referential integrity
- ❌ Hard to query relationships

### After (Database)
- ✅ Dynamic runtime modifications
- ✅ Admin interface possible
- ✅ Database referential integrity
- ✅ Efficient querying with indexes
- ✅ Foreign key relationships
- ✅ Audit trail (created_at, updated_at)
- ✅ Can be edited via API/UI
- ⚠️ Requires migration to populate

## Future Enhancements

1. **Admin API endpoints** to create/update/delete curriculum items
2. **Versioning** for curriculum changes over time
3. **Localization** support for multiple languages
4. **Standards mapping** (Common Core, state standards)
5. **Learning path** recommendations based on prerequisite graph
6. **Curriculum analytics** (most/least practiced topics)
7. **Custom curriculum** for schools/teachers
8. **Concept dependency visualization** tools
