"""
Repository abstraction layer for persistence.

Defines repository interfaces (Protocols) for Problem and Attempt storage,
with JSONL-based implementations. Future DB implementations can implement
these same interfaces without changing the API layer.
"""

from typing import Optional, Protocol, Sequence, Union
from pathlib import Path

from models import Problem
from tracking import Attempt, save_attempt as jsonl_save_attempt, load_attempts as jsonl_load_attempts, save_attempts_batch as jsonl_save_batch_attempts, clear_attempts_file
from storage import problem_to_dict, dict_to_problem, save_problem as jsonl_save_problem, load_problems as jsonl_load_problems, save_problems_batch as jsonl_save_batch, clear_problems_file
import json


# ============================================================================
# Repository Protocols (Interfaces)
# ============================================================================


class ProblemRepository(Protocol):
    """
    Interface for problem persistence.

    Implementations can use JSONL, PostgreSQL, or other backends
    as long as they satisfy this protocol.
    """

    def save_problem(self, problem: Problem) -> None:
        """Save a single problem."""
        ...

    def get_problem(self, problem_id: str) -> Optional[Problem]:
        """Retrieve a problem by ID."""
        ...

    def list_problems_by_topic(self, topic_id: str, limit: int = 50) -> Sequence[Problem]:
        """List problems for a given topic, up to limit."""
        ...

    def list_all_problems(self, limit: int = 100) -> Sequence[Problem]:
        """List all problems up to limit."""
        ...


class AttemptRepository(Protocol):
    """
    Interface for attempt/tracking persistence.

    Implementations can use JSONL, PostgreSQL, or other backends
    as long as they satisfy this protocol.
    """

    def save_attempt(self, attempt: Attempt) -> None:
        """Save a single attempt."""
        ...

    def list_attempts_by_user_and_topic(
        self, user_id: str, topic_id: str
    ) -> Sequence[Attempt]:
        """List all attempts by a user on a specific topic."""
        ...

    def list_attempts_by_user(self, user_id: str) -> Sequence[Attempt]:
        """List all attempts by a user across all topics."""
        ...

    def list_all_attempts(self, limit: int = 100) -> Sequence[Attempt]:
        """List all attempts up to limit."""
        ...

    def list_attempts(self, limit: int = 100) -> Sequence[Attempt]:
        """Alias for list_all_attempts to match API usage."""
        ...


# ============================================================================
# JSONL-Based Repository Implementations
# ============================================================================


class JSONLProblemRepository:
    """
    Problem repository backed by JSONL files.

    Wraps existing storage.py functionality.
    """

    def __init__(self, path: Union[str, Path] = "data/problems.jsonl"):
        """
        Initialize with path to JSONL file.

        Args:
            path: Path to problems.jsonl file
        """
        self.path = str(path)

    def save_problem(self, problem: Problem) -> None:
        """Save a single problem to JSONL."""
        jsonl_save_problem(problem, self.path)

    def get_problem(self, problem_id: str) -> Optional[Problem]:
        """Retrieve a problem by ID (linear search)."""
        try:
            problems = jsonl_load_problems(self.path)
            for problem in problems:
                if problem.id == problem_id:
                    return problem
        except FileNotFoundError:
            pass
        return None

    def list_problems_by_topic(self, topic_id: str, limit: int = 50) -> Sequence[Problem]:
        """List problems for a given topic."""
        try:
            all_problems = jsonl_load_problems(self.path)
            result = [p for p in all_problems if p.topic_id == topic_id]
            return result[:limit]
        except FileNotFoundError:
            return []

    def list_all_problems(self, limit: int = 100) -> Sequence[Problem]:
        """List all problems up to limit."""
        try:
            all_problems = jsonl_load_problems(self.path)
            return all_problems[:limit]
        except FileNotFoundError:
            return []


class JSONLAttemptRepository:
    """
    Attempt repository backed by JSONL files.

    Wraps existing tracking.py functionality.
    """

    def __init__(self, path: Union[str, Path] = "data/attempts.jsonl"):
        """
        Initialize with path to JSONL file.

        Args:
            path: Path to attempts.jsonl file
        """
        self.path = str(path)

    def save_attempt(self, attempt: Attempt) -> None:
        """Save a single attempt to JSONL."""
        jsonl_save_attempt(attempt, self.path)

    def list_attempts_by_user_and_topic(
        self, user_id: str, topic_id: str
    ) -> Sequence[Attempt]:
        """List all attempts by a user on a specific topic."""
        try:
            all_attempts = jsonl_load_attempts(self.path)
            result = [
                a for a in all_attempts
                if a.user_id == user_id and a.topic_id == topic_id
            ]
            return result
        except FileNotFoundError:
            return []

    def list_attempts_by_user(self, user_id: str) -> Sequence[Attempt]:
        """List all attempts by a user across all topics."""
        try:
            all_attempts = jsonl_load_attempts(self.path)
            result = [a for a in all_attempts if a.user_id == user_id]
            return result
        except FileNotFoundError:
            return []

    def list_all_attempts(self, limit: int = 100) -> Sequence[Attempt]:
        """List all attempts up to limit."""
        try:
            all_attempts = jsonl_load_attempts(self.path)
            return all_attempts[:limit]
        except FileNotFoundError:
            return []

    def list_attempts(self, limit: int = 100) -> Sequence[Attempt]:
        """Alias used by teacher endpoints; returns same as list_all_attempts."""
        return self.list_all_attempts(limit)


# ============================================================================
# Database Repository Implementations
# ============================================================================


class DBProblemRepository:
    """
    PostgreSQL-backed problem repository using SQLAlchemy.
    
    Provides the same interface as JSONLProblemRepository but uses
    a relational database for storage and querying.
    """

    def __init__(self, session_factory):
        """
        Initialize with SQLAlchemy session factory.

        Args:
            session_factory: Callable that returns a SQLAlchemy Session
        """
        self.session_factory = session_factory

    def save_problem(self, problem: Problem) -> None:
        """Save a single problem to database."""
        from db_models import ProblemRecord
        
        session = self.session_factory()
        try:
            # Check if problem already exists
            existing = session.query(ProblemRecord).filter_by(id=problem.id).first()
            if existing:
                session.delete(existing)
            
            # Convert problem to database record
            problem_dict = problem_to_dict(problem)
            record = ProblemRecord(
                id=problem.id,
                course_id=problem.course_id,
                unit_id=problem.unit_id,
                topic_id=problem.topic_id,
                difficulty=problem.difficulty,
                calculator_mode=problem.calculator_mode,
                prompt_latex=problem.prompt_latex,
                answer_type=problem.answer_type,
                final_answer_json=json.dumps(str(problem.final_answer)),
                solution_json=json.dumps(problem_dict.get("solution", {})),
                metadata_json=json.dumps(problem_dict.get("metadata", {})),
            )
            session.add(record)
            session.commit()
        finally:
            session.close()

    def get_problem(self, problem_id: str) -> Optional[Problem]:
        """Retrieve a problem by ID from database."""
        from db_models import ProblemRecord
        
        session = self.session_factory()
        try:
            record = session.query(ProblemRecord).filter_by(id=problem_id).first()
            if not record:
                return None
            
            # Reconstruct Problem from record
            return self._record_to_problem(record)
        finally:
            session.close()

    def list_problems_by_topic(self, topic_id: str, limit: int = 50) -> Sequence[Problem]:
        """List problems for a given topic from database."""
        from db_models import ProblemRecord
        
        session = self.session_factory()
        try:
            records = session.query(ProblemRecord).filter_by(
                topic_id=topic_id
            ).limit(limit).all()
            
            return [self._record_to_problem(r) for r in records]
        finally:
            session.close()

    def list_all_problems(self, limit: int = 100) -> Sequence[Problem]:
        """List all problems from database."""
        from db_models import ProblemRecord
        
        session = self.session_factory()
        try:
            records = session.query(ProblemRecord).limit(limit).all()
            return [self._record_to_problem(r) for r in records]
        finally:
            session.close()

    def _record_to_problem(self, record) -> Problem:
        """Convert a ProblemRecord to a Problem instance."""
        return dict_to_problem({
            "id": record.id,
            "course_id": record.course_id,
            "unit_id": record.unit_id,
            "topic_id": record.topic_id,
            "difficulty": record.difficulty,
            "calculator_mode": record.calculator_mode,
            "prompt_latex": record.prompt_latex,
            "answer_type": record.answer_type,
            "final_answer": json.loads(record.final_answer_json),
            "solution": json.loads(record.solution_json),
            "metadata": json.loads(record.metadata_json),
        })


class DBAttemptRepository:
    """
    PostgreSQL-backed attempt repository using SQLAlchemy.
    
    Provides the same interface as JSONLAttemptRepository but uses
    a relational database for storage and querying.
    """

    def __init__(self, session_factory):
        """
        Initialize with SQLAlchemy session factory.

        Args:
            session_factory: Callable that returns a SQLAlchemy Session
        """
        self.session_factory = session_factory

    def save_attempt(self, attempt: Attempt) -> None:
        """Save a single attempt to database."""
        from db_models import AttemptRecord
        
        session = self.session_factory()
        try:
            record = AttemptRecord(
                user_id=attempt.user_id,
                problem_id=attempt.problem_id,
                topic_id=attempt.topic_id,
                course_id=attempt.course_id,
                difficulty=attempt.difficulty,
                is_correct=attempt.is_correct,
                timestamp=attempt.timestamp,
                time_taken_seconds=attempt.time_taken_seconds,
            )
            session.add(record)
            session.commit()
        finally:
            session.close()

    def list_attempts_by_user_and_topic(
        self, user_id: str, topic_id: str
    ) -> Sequence[Attempt]:
        """List all attempts by a user on a specific topic from database."""
        from db_models import AttemptRecord
        
        session = self.session_factory()
        try:
            records = session.query(AttemptRecord).filter_by(
                user_id=user_id,
                topic_id=topic_id
            ).all()
            
            return [self._record_to_attempt(r) for r in records]
        finally:
            session.close()

    def list_attempts_by_user(self, user_id: str) -> Sequence[Attempt]:
        """List all attempts by a user across all topics from database."""
        from db_models import AttemptRecord
        
        session = self.session_factory()
        try:
            records = session.query(AttemptRecord).filter_by(
                user_id=user_id
            ).all()
            
            return [self._record_to_attempt(r) for r in records]
        finally:
            session.close()

    def list_all_attempts(self, limit: int = 1000) -> Sequence[Attempt]:
        """List all attempts from database."""
        from db_models import AttemptRecord
        
        session = self.session_factory()
        try:
            records = session.query(AttemptRecord).limit(limit).all()
            return [self._record_to_attempt(r) for r in records]
        finally:
            session.close()

    def list_attempts(self, limit: int = 1000) -> Sequence[Attempt]:
        """Alias used by teacher endpoints; returns same as list_all_attempts."""
        return self.list_all_attempts(limit)

    def _record_to_attempt(self, record) -> Attempt:
        """Convert an AttemptRecord to an Attempt instance."""
        return Attempt(
            user_id=record.user_id,
            problem_id=record.problem_id,
            topic_id=record.topic_id,
            course_id=record.course_id,
            difficulty=record.difficulty,
            is_correct=record.is_correct,
            timestamp=record.timestamp,
            time_taken_seconds=record.time_taken_seconds,
        )
