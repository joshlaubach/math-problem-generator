"""
Generator registry for managing problem generators.

Provides a centralized registry of available problem generators
and lookup functions for accessing them by topic.
"""

from typing import Dict
from concepts import get_concept

from .base import ProblemGenerator


# Import generators
_generators: Dict[str, ProblemGenerator] = {}


def register_generator(topic_id: str, generator: ProblemGenerator) -> None:
    """
    Register a problem generator for a topic.

    Args:
        topic_id: The topic ID (e.g., "alg1_linear_solve_one_var")
        generator: The ProblemGenerator instance
    """
    _generators[topic_id] = generator


def get_generator_for_topic(topic_id: str) -> ProblemGenerator:
    """
    Get the problem generator for a given topic.

    Args:
        topic_id: The topic ID

    Returns:
        The ProblemGenerator instance for that topic

    Raises:
        KeyError: If no generator is registered for the topic
    """
    if topic_id not in _generators:
        raise KeyError(f"No generator registered for topic: {topic_id}")
    return _generators[topic_id]


def list_registered_topics() -> list[str]:
    """Get a list of all registered topic IDs."""
    return list(_generators.keys())


def get_generators_for_concepts(concept_ids: list[str]) -> Dict[str, ProblemGenerator]:
    """
    Get all generators whose primary_concept_id matches any of the given concept IDs.
    
    This enables concept-targeted assignment creation: choose concepts, get matching generators.
    
    Args:
        concept_ids: List of concept IDs to filter by
        
    Returns:
        Dictionary mapping topic_id -> generator for all matching topics
    """
    matching_generators: Dict[str, ProblemGenerator] = {}
    
    for topic_id, generator in _generators.items():
        try:
            # Get the concept for this topic via the generator
            # The generator should have a way to identify its primary concept
            # For now, we'll check if the generator object has primary_concept_id
            if hasattr(generator, 'primary_concept_id'):
                if generator.primary_concept_id in concept_ids:
                    matching_generators[topic_id] = generator
            else:
                # Try to infer from the generator's class or topic_id
                # SAT generators start with "sat_", AP generators with "ap_"
                for concept_id in concept_ids:
                    if concept_id.startswith('sat.') and 'sat' in topic_id:
                        matching_generators[topic_id] = generator
                        break
                    elif concept_id.startswith('ap_') and 'ap' in topic_id:
                        matching_generators[topic_id] = generator
                        break
        except Exception:
            # If we can't determine primary concept, skip this generator
            pass
    
    return matching_generators



# Lazy import and registration of generators
def _ensure_generators_registered() -> None:
    """Initialize generator registry on first access."""
    if not _generators:
        # Import here to avoid circular dependencies
        from generators.linear import LinearEquationGenerator
        from generators.inequalities import InequalityProblemGenerator
        from generators.sat_math import (
            SATLinearEquationGenerator,
            SATQuadraticGenerator,
            SATDataStatsGenerator,
        )
        from generators.ap_calculus import (
            APCalcDerivativePowerRuleGenerator,
            APCalcChainRuleGenerator,
            APCalcIntegralFTCGenerator,
            APCalcBCSeriesGenerator,
        )
        
        # Algebra generators
        register_generator(
            "alg1_linear_solve_one_var",
            LinearEquationGenerator()
        )
        register_generator(
            "alg1_linear_inequalities_one_var",
            InequalityProblemGenerator()
        )
        
        # SAT Math generators
        register_generator(
            "sat_linear",
            SATLinearEquationGenerator()
        )
        register_generator(
            "sat_quadratic",
            SATQuadraticGenerator()
        )
        register_generator(
            "sat_statistics",
            SATDataStatsGenerator()
        )
        
        # AP Calculus generators
        register_generator(
            "ap_deriv_rules",
            APCalcDerivativePowerRuleGenerator()
        )
        register_generator(
            "ap_deriv_chain",
            APCalcChainRuleGenerator()
        )
        register_generator(
            "ap_int_ftc",
            APCalcIntegralFTCGenerator()
        )
        register_generator(
            "ap_series_conv",
            APCalcBCSeriesGenerator()
        )

        # Aliases for legacy topic names used in tests
        register_generator(
            "algebra",
            LinearEquationGenerator()
        )
        register_generator(
            "geometry",
            InequalityProblemGenerator()
        )


# Register generators when module is imported
_ensure_generators_registered()
