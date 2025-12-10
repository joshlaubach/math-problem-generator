"""
Migration script to populate curriculum database tables from existing code-defined taxonomy.

This script:
1. Creates education levels (High School, College/University, Test Prep)
2. Migrates courses from existing taxonomy
3. Migrates units and topics
4. Migrates concepts from concept registry

Run with: python migrate_curriculum_to_db.py
"""

import json
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from db_models import (
    Base,
    EducationLevelRecord,
    CourseRecord,
    UnitRecord,
    TopicRecord,
    ConceptRecord,
)
from db_session import get_engine
from concepts import CONCEPTS

# Import all concept modules to populate CONCEPTS registry
import prealg_concepts
import alg1_concepts
import alg2_concepts
import geometry_concepts
import precalc_concepts
import ap_calculus_concepts
import calc1_concepts
import calc2_concepts
import calc3_concepts
import diffeq_concepts
import linalg_concepts
import probstat_concepts
import sat_math_concepts
import proofs_contest_concepts


def create_education_levels(session: Session) -> None:
    """Create the three main education levels."""
    levels = [
        EducationLevelRecord(
            id="high_school",
            name="High School",
            description="High school mathematics curriculum including Pre-Algebra through Pre-Calculus",
            display_order=1,
            is_active=True,
        ),
        EducationLevelRecord(
            id="college_university",
            name="College/University",
            description="College-level mathematics including Calculus, Linear Algebra, Differential Equations",
            display_order=2,
            is_active=True,
        ),
        EducationLevelRecord(
            id="test_prep",
            name="Test Prep",
            description="Standardized test preparation including SAT, ACT, AP, and contest mathematics",
            display_order=3,
            is_active=True,
        ),
    ]
    
    for level in levels:
        existing = session.query(EducationLevelRecord).filter_by(id=level.id).first()
        if not existing:
            session.add(level)
            print(f"✓ Created education level: {level.name}")
    
    session.commit()


def create_courses(session: Session) -> None:
    """Create courses categorized by education level."""
    courses = [
        # High School Courses
        CourseRecord(
            id="pre_algebra",
            name="Pre-Algebra",
            description="Foundation mathematics including integers, fractions, decimals, ratios, and basic equations",
            education_level_id="high_school",
            display_order=1,
            code="PREALG",
            is_active=True,
        ),
        CourseRecord(
            id="algebra_1",
            name="Algebra 1",
            description="First-year algebra including linear equations, inequalities, systems, exponents, and polynomials",
            education_level_id="high_school",
            display_order=2,
            code="ALG1",
            prerequisites_json=json.dumps(["pre_algebra"]),
            is_active=True,
        ),
        CourseRecord(
            id="geometry",
            name="Geometry",
            description="Plane and solid geometry, proofs, congruence, similarity, area, and volume",
            education_level_id="high_school",
            display_order=3,
            code="GEOM",
            prerequisites_json=json.dumps(["algebra_1"]),
            is_active=True,
        ),
        CourseRecord(
            id="algebra_2",
            name="Algebra 2",
            description="Advanced algebra including quadratics, exponentials, logarithms, rational functions, and sequences",
            education_level_id="high_school",
            display_order=4,
            code="ALG2",
            prerequisites_json=json.dumps(["algebra_1"]),
            is_active=True,
        ),
        CourseRecord(
            id="precalculus",
            name="Pre-Calculus",
            description="Preparation for calculus including trigonometry, polar coordinates, complex numbers, and limits",
            education_level_id="high_school",
            display_order=5,
            code="PRECALC",
            prerequisites_json=json.dumps(["algebra_2"]),
            is_active=True,
        ),
        
        # College/University Courses
        CourseRecord(
            id="calculus_1",
            name="Calculus I",
            description="Single-variable calculus: limits, derivatives, applications of derivatives, and integration",
            education_level_id="college_university",
            display_order=1,
            code="CALC1",
            credits=4.0,
            prerequisites_json=json.dumps(["precalculus"]),
            is_active=True,
        ),
        CourseRecord(
            id="calculus_2",
            name="Calculus II",
            description="Integration techniques, sequences and series, parametric equations, and polar coordinates",
            education_level_id="college_university",
            display_order=2,
            code="CALC2",
            credits=4.0,
            prerequisites_json=json.dumps(["calculus_1"]),
            is_active=True,
        ),
        CourseRecord(
            id="calculus_3",
            name="Calculus III (Multivariable Calculus)",
            description="Multivariable calculus including vectors, partial derivatives, multiple integrals, and vector calculus",
            education_level_id="college_university",
            display_order=3,
            code="CALC3",
            credits=4.0,
            prerequisites_json=json.dumps(["calculus_2"]),
            is_active=True,
        ),
        CourseRecord(
            id="linear_algebra",
            name="Linear Algebra",
            description="Vector spaces, matrices, linear transformations, eigenvalues, and applications",
            education_level_id="college_university",
            display_order=4,
            code="LINALG",
            credits=3.0,
            prerequisites_json=json.dumps(["calculus_1"]),
            is_active=True,
        ),
        CourseRecord(
            id="differential_equations",
            name="Differential Equations",
            description="Ordinary differential equations, systems of ODEs, Laplace transforms, and applications",
            education_level_id="college_university",
            display_order=5,
            code="DIFFEQ",
            credits=3.0,
            prerequisites_json=json.dumps(["calculus_2", "linear_algebra"]),
            is_active=True,
        ),
        CourseRecord(
            id="probability_statistics",
            name="Probability and Statistics",
            description="Probability theory, random variables, distributions, hypothesis testing, and regression",
            education_level_id="college_university",
            display_order=6,
            code="PROBSTAT",
            credits=3.0,
            prerequisites_json=json.dumps(["calculus_1"]),
            is_active=True,
        ),
        
        # Test Prep Courses
        CourseRecord(
            id="sat_math",
            name="SAT Math",
            description="SAT mathematics preparation covering algebra, problem solving, data analysis, and advanced math",
            education_level_id="test_prep",
            display_order=1,
            code="SAT",
            is_active=True,
        ),
        CourseRecord(
            id="ap_calculus_ab",
            name="AP Calculus AB",
            description="Advanced Placement Calculus AB: derivatives, integrals, and applications",
            education_level_id="test_prep",
            display_order=2,
            code="APCALCAB",
            prerequisites_json=json.dumps(["precalculus"]),
            is_active=True,
        ),
        CourseRecord(
            id="ap_calculus_bc",
            name="AP Calculus BC",
            description="Advanced Placement Calculus BC: all of AB plus sequences, series, and parametric equations",
            education_level_id="test_prep",
            display_order=3,
            code="APCALCBC",
            prerequisites_json=json.dumps(["ap_calculus_ab"]),
            is_active=True,
        ),
        CourseRecord(
            id="contest_math",
            name="Math Contest Problems",
            description="Competition mathematics including AMC, AIME, USAMO, and proof-based problem solving",
            education_level_id="test_prep",
            display_order=4,
            code="CONTEST",
            is_active=True,
        ),
    ]
    
    for course in courses:
        existing = session.query(CourseRecord).filter_by(id=course.id).first()
        if not existing:
            session.add(course)
            print(f"✓ Created course: {course.name} ({course.education_level_id})")
    
    session.commit()


def migrate_concepts_to_db(session: Session) -> None:
    """Migrate all concepts from CONCEPTS registry to database."""
    print(f"\nMigrating {len(CONCEPTS)} concepts to database...")
    
    for concept_id, concept in CONCEPTS.items():
        existing = session.query(ConceptRecord).filter_by(id=concept.id).first()
        if not existing:
            concept_record = ConceptRecord(
                id=concept.id,
                name=concept.name,
                description=concept.description,
                topic_id=concept.topic_id,
                unit_id=concept.unit_id,
                course_id=concept.course_id,
                kind=concept.kind,
                difficulty_min=concept.difficulty_min,
                difficulty_max=concept.difficulty_max,
                prerequisites_json=json.dumps(concept.prerequisites),
                examples_latex_json=json.dumps(concept.examples_latex),
                tags_json=json.dumps(concept.tags),
                version=concept.version or "v1",
                is_active=True,
            )
            session.add(concept_record)
    
    session.commit()
    print(f"✓ Migrated {len(CONCEPTS)} concepts to database")


def verify_migration(session: Session) -> None:
    """Verify the migration was successful."""
    print("\n" + "="*60)
    print("MIGRATION VERIFICATION")
    print("="*60)
    
    level_count = session.query(EducationLevelRecord).count()
    print(f"Education Levels: {level_count}")
    
    course_count = session.query(CourseRecord).count()
    print(f"Courses: {course_count}")
    
    for level in session.query(EducationLevelRecord).order_by(EducationLevelRecord.display_order):
        courses = session.query(CourseRecord).filter_by(education_level_id=level.id).count()
        print(f"  - {level.name}: {courses} courses")
    
    unit_count = session.query(UnitRecord).count()
    topic_count = session.query(TopicRecord).count()
    concept_count = session.query(ConceptRecord).count()
    
    print(f"Units: {unit_count}")
    print(f"Topics: {topic_count}")
    print(f"Concepts: {concept_count}")
    
    print("\nTop 5 courses by concept count:")
    for course in session.query(CourseRecord).order_by(CourseRecord.display_order).limit(5):
        concepts = session.query(ConceptRecord).filter_by(course_id=course.id).count()
        print(f"  - {course.name}: {concepts} concepts")


def main():
    """Run the migration."""
    print("Starting curriculum migration to database...")
    print("="*60)
    
    # Get database engine
    engine = get_engine()
    
    # Create all tables
    print("\nCreating database tables...")
    Base.metadata.create_all(engine)
    print("✓ Tables created")
    
    # Run migrations
    with Session(engine) as session:
        print("\nCreating education levels...")
        create_education_levels(session)
        
        print("\nCreating courses...")
        create_courses(session)
        
        print("\nMigrating concepts...")
        migrate_concepts_to_db(session)
        
        print("\nVerifying migration...")
        verify_migration(session)
    
    print("\n" + "="*60)
    print("✓ Migration completed successfully!")
    print("="*60)


if __name__ == "__main__":
    main()
