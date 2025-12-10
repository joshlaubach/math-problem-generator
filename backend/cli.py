"""
Command-line interface for the problem generator.

Provides a CLI to generate problems on demand with various options.

Usage:
    python cli.py --topic_id alg1_linear_solve_one_var --difficulty 2
    python cli.py --topic_id alg1_linear_solve_one_var --difficulty 3 --show-steps
"""

import argparse
from pathlib import Path

from generators import get_generator_for_topic, list_registered_topics
from models import CalculatorMode
from storage import save_problem


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Generate math problems"
    )
    
    parser.add_argument(
        "--topic_id",
        type=str,
        required=True,
        help=f"Topic ID (available: {', '.join(list_registered_topics())})"
    )
    
    parser.add_argument(
        "--difficulty",
        type=int,
        required=True,
        help="Difficulty level (typically 1-4)"
    )
    
    parser.add_argument(
        "--calculator_mode",
        type=str,
        default="none",
        choices=["none", "scientific", "graphing"],
        help="Calculator mode allowed"
    )
    
    parser.add_argument(
        "--show-steps",
        action="store_true",
        help="Show step-by-step solution"
    )
    
    parser.add_argument(
        "--save",
        type=str,
        help="Save generated problem to JSONL file (path)"
    )
    
    args = parser.parse_args()
    
    # Get generator
    try:
        generator = get_generator_for_topic(args.topic_id)
    except KeyError as e:
        print(f"Error: {e}")
        print(f"Available topics: {', '.join(list_registered_topics())}")
        return 1
    
    # Generate problem
    try:
        problem = generator.generate(
            difficulty=args.difficulty,
            calculator_mode=args.calculator_mode
        )
    except ValueError as e:
        print(f"Error: {e}")
        return 1
    
    # Display problem
    print("\n" + "=" * 70)
    print(f"Problem (Difficulty {problem.difficulty})")
    print("=" * 70)
    print(f"\n{problem.prompt_latex}\n")
    
    solution = problem.metadata.get("solution")
    if solution:
        print("-" * 70)
        print("Solution")
        print("-" * 70)
        print(f"\nFinal Answer: ${solution.final_answer_latex}$")
        print(f"Verified: {solution.sympy_verified}\n")
        
        if args.show_steps:
            print("Step-by-step solution:\n")
            for step in solution.steps:
                print(f"Step {step.index + 1}: {step.description_latex}")
                print(f"         {step.expression_latex}\n")
    
    # Save if requested
    if args.save:
        save_problem(problem, args.save)
        print(f"\n✓ Problem saved to {args.save}")
    
    print("=" * 70 + "\n")
    return 0


if __name__ == "__main__":
    exit(main())
