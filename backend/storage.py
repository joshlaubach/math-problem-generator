"""
Problem and solution storage using JSON.

Provides serialization and persistence for Problem and Solution objects
to JSONL (JSON Lines) format for easy archiving and analysis.
"""

import json
from pathlib import Path
from typing import Any, Dict

from models import Problem, Solution, SolutionStep, CalculatorMode


def problem_to_dict(problem: Problem) -> Dict[str, Any]:
    """
    Convert a Problem to a JSON-serializable dictionary.

    Args:
        problem: The Problem instance to serialize

    Returns:
        A dictionary containing all problem and solution information
    """
    solution = problem.metadata.get("solution")
    
    solution_dict = None
    if solution:
        steps_list = [
            {
                "index": step.index,
                "description_latex": step.description_latex,
                "expression_latex": step.expression_latex
            }
            for step in solution.steps
        ]
        
        solution_dict = {
            "steps": steps_list,
            "final_answer_latex": solution.final_answer_latex,
            "full_solution_latex": solution.full_solution_latex,
            "sympy_verified": solution.sympy_verified,
            "verification_details": solution.verification_details
        }
    
    return {
        "id": problem.id,
        "course_id": problem.course_id,
        "unit_id": problem.unit_id,
        "topic_id": problem.topic_id,
        "difficulty": problem.difficulty,
        "calculator_mode": problem.calculator_mode,
        "prompt_latex": problem.prompt_latex,
        "answer_type": problem.answer_type,
        "final_answer": str(problem.final_answer),
        "concept_ids": problem.concept_ids,
        "primary_concept_id": problem.primary_concept_id,
        "solution": solution_dict
    }


def dict_to_problem(data: Dict[str, Any]) -> Problem:
    """
    Reconstruct a Problem from a dictionary.

    Args:
        data: Dictionary created by problem_to_dict()

    Returns:
        A Problem instance (note: full SymPy reconstruction not included;
        solution is reconstructed from stored LaTeX/text forms)
    """
    solution_data = data.get("solution")
    
    solution = None
    if solution_data:
        steps = [
            SolutionStep(
                index=step["index"],
                description_latex=step["description_latex"],
                expression_latex=step["expression_latex"]
            )
            for step in solution_data.get("steps", [])
        ]
        
        solution = Solution(
            steps=steps,
            final_answer_latex=solution_data.get("final_answer_latex", ""),
            full_solution_latex=solution_data.get("full_solution_latex", ""),
            sympy_verified=solution_data.get("sympy_verified", False),
            verification_details=solution_data.get("verification_details")
        )
    
    metadata = {}
    if solution:
        metadata["solution"] = solution
    
    return Problem(
        id=data["id"],
        course_id=data["course_id"],
        unit_id=data["unit_id"],
        topic_id=data["topic_id"],
        difficulty=data["difficulty"],
        calculator_mode=data["calculator_mode"],
        prompt_latex=data["prompt_latex"],
        answer_type=data["answer_type"],
        final_answer=data["final_answer"],  # Stored as string
        concept_ids=data.get("concept_ids", []),  # Backward compatible: default to empty list
        primary_concept_id=data.get("primary_concept_id"),  # Backward compatible: default to None
        metadata=metadata
    )


def save_problem(problem: Problem, path: str | Path) -> None:
    """
    Save a problem to a JSONL file.

    Appends the problem as a JSON line to the file at the given path.

    Args:
        problem: The Problem to save
        path: Path to the JSONL file
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    problem_dict = problem_to_dict(problem)
    
    with open(path, 'a') as f:
        f.write(json.dumps(problem_dict) + '\n')


def load_problems(path: str | Path) -> list[Problem]:
    """
    Load problems from a JSONL file.

    Args:
        path: Path to the JSONL file

    Returns:
        List of Problem instances

    Raises:
        FileNotFoundError: If the file does not exist
    """
    path = Path(path)
    
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    
    problems = []
    with open(path, 'r') as f:
        for line in f:
            line = line.strip()
            if line:
                data = json.loads(line)
                problem = dict_to_problem(data)
                problems.append(problem)
    
    return problems


def save_problems_batch(problems: list[Problem], path: str | Path) -> None:
    """
    Save multiple problems to a JSONL file.

    Args:
        problems: List of Problem instances
        path: Path to the JSONL file
    """
    for problem in problems:
        save_problem(problem, path)


def clear_problems_file(path: str | Path) -> None:
    """
    Clear (truncate) a problems file.

    Args:
        path: Path to the JSONL file
    """
    path = Path(path)
    if path.exists():
        path.unlink()
