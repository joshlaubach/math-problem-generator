"""
Repository for assignment persistence.

Handles storage and retrieval of assignments and their associated problems.
"""

from typing import Optional, Protocol, Sequence
from datetime import datetime
from sqlalchemy.orm import Session
from db_models import AssignmentRecord, AssignmentProblemRecord
from assignments_models import (
    Assignment,
    AssignmentProblemLink,
    generate_assignment_code,
)


class AssignmentRepository(Protocol):
    """Protocol for assignment storage operations."""

    def create_assignment(self, assignment: Assignment) -> None:
        """Create a new assignment."""
        ...

    def get_assignment(self, assignment_id: str) -> Optional[Assignment]:
        """Retrieve an assignment by ID."""
        ...

    def list_assignments_for_teacher(self, teacher_id: str) -> Sequence[Assignment]:
        """List all assignments for a specific teacher."""
        ...

    def list_active_assignments(self) -> Sequence[Assignment]:
        """List all active assignments."""
        ...

    def add_problem_links(self, links: list[AssignmentProblemLink]) -> None:
        """Add problem links to an assignment."""
        ...

    def list_assignment_problems(
        self, assignment_id: str
    ) -> Sequence[AssignmentProblemLink]:
        """Get all problems for an assignment in order."""
        ...


def assignment_record_to_model(record: AssignmentRecord) -> Assignment:
    """Convert a database record to an Assignment model."""
    return Assignment(
        id=record.id,
        name=record.name,
        description=record.description,
        teacher_id=record.teacher_id,
        created_at=record.created_at,
        status=record.status,  # type: ignore
        topic_id=record.topic_id,
        num_questions=record.num_questions,
        min_difficulty=record.min_difficulty,
        max_difficulty=record.max_difficulty,
        calculator_mode=record.calculator_mode,  # type: ignore
    )


def assignment_model_to_record(model: Assignment) -> AssignmentRecord:
    """Convert an Assignment model to a database record."""
    return AssignmentRecord(
        id=model.id,
        name=model.name,
        description=model.description,
        teacher_id=model.teacher_id,
        created_at=model.created_at,
        status=model.status,
        topic_id=model.topic_id,
        num_questions=model.num_questions,
        min_difficulty=model.min_difficulty,
        max_difficulty=model.max_difficulty,
        calculator_mode=model.calculator_mode,
    )


def problem_link_record_to_model(
    record: AssignmentProblemRecord,
) -> AssignmentProblemLink:
    """Convert a database record to an AssignmentProblemLink model."""
    return AssignmentProblemLink(
        assignment_id=record.assignment_id,
        problem_id=record.problem_id,
        index=record.index,
    )


def problem_link_model_to_record(
    model: AssignmentProblemLink,
) -> AssignmentProblemRecord:
    """Convert an AssignmentProblemLink model to a database record."""
    return AssignmentProblemRecord(
        assignment_id=model.assignment_id,
        problem_id=model.problem_id,
        index=model.index,
    )


class DBAssignmentRepository:
    """Database-backed assignment repository."""

    def __init__(self, get_session):
        """Initialize with a session factory."""
        self.get_session = get_session

    def create_assignment(self, assignment: Assignment) -> None:
        """Create a new assignment in the database."""
        session: Session = self.get_session()
        try:
            record = assignment_model_to_record(assignment)
            session.add(record)
            session.commit()
        finally:
            session.close()

    def get_assignment(self, assignment_id: str) -> Optional[Assignment]:
        """Retrieve an assignment by ID."""
        session: Session = self.get_session()
        try:
            record = session.query(AssignmentRecord).filter_by(id=assignment_id).first()
            if record:
                return assignment_record_to_model(record)
            return None
        finally:
            session.close()

    def list_assignments_for_teacher(self, teacher_id: str) -> Sequence[Assignment]:
        """List all assignments created by a teacher."""
        session: Session = self.get_session()
        try:
            records = (
                session.query(AssignmentRecord)
                .filter_by(teacher_id=teacher_id)
                .order_by(AssignmentRecord.created_at.desc())
                .all()
            )
            return [assignment_record_to_model(r) for r in records]
        finally:
            session.close()

    def list_active_assignments(self) -> Sequence[Assignment]:
        """List all active assignments."""
        session: Session = self.get_session()
        try:
            records = (
                session.query(AssignmentRecord)
                .filter_by(status="active")
                .order_by(AssignmentRecord.created_at.desc())
                .all()
            )
            return [assignment_record_to_model(r) for r in records]
        finally:
            session.close()

    def add_problem_links(self, links: list[AssignmentProblemLink]) -> None:
        """Add problem links to an assignment."""
        session: Session = self.get_session()
        try:
            records = [problem_link_model_to_record(link) for link in links]
            session.add_all(records)
            session.commit()
        finally:
            session.close()

    def list_assignment_problems(
        self, assignment_id: str
    ) -> Sequence[AssignmentProblemLink]:
        """Get all problems for an assignment in order."""
        session: Session = self.get_session()
        try:
            records = (
                session.query(AssignmentProblemRecord)
                .filter_by(assignment_id=assignment_id)
                .order_by(AssignmentProblemRecord.index)
                .all()
            )
            return [problem_link_record_to_model(r) for r in records]
        finally:
            session.close()


class InMemoryAssignmentRepository:
    """Lightweight in-memory assignment store for tests and JSONL mode."""

    def __init__(self) -> None:
        self._assignments: dict[str, Assignment] = {}
        self._problem_links: list[AssignmentProblemLink] = []

    def create_assignment(self, assignment: Assignment) -> None:
        self._assignments[assignment.id] = assignment

    def get_assignment(self, assignment_id: str) -> Optional[Assignment]:
        return self._assignments.get(assignment_id)

    def list_assignments_for_teacher(self, teacher_id: str) -> Sequence[Assignment]:
        return [a for a in self._assignments.values() if a.teacher_id == teacher_id]

    def list_active_assignments(self) -> Sequence[Assignment]:
        return [a for a in self._assignments.values() if a.status == "active"]

    def add_problem_links(self, links: list[AssignmentProblemLink]) -> None:
        self._problem_links.extend(links)

    def list_assignment_problems(
        self, assignment_id: str
    ) -> Sequence[AssignmentProblemLink]:
        return [l for l in self._problem_links if l.assignment_id == assignment_id]
