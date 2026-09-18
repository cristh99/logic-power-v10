"""Declarative solver capabilities and fail-closed eligibility rules."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .problem_ir import Horizon, ModelStatus, ProblemIR, UncertaintyKind


Eligibility = Callable[[ProblemIR, frozenset[str]], tuple[str, ...]]


@dataclass(frozen=True)
class SolverCapability:
    name: str
    exactness: str
    cost_rank: int
    description: str
    eligibility: Eligibility


def _logic_exact(
    problem: ProblemIR, classes: frozenset[str]
) -> tuple[str, ...]:
    del problem
    missing: list[str] = []
    if "PLANNING" in classes:
        missing.append("action_planner_required")
    if "GAME" in classes:
        missing.append("strategic_solver_required")
    if not ({"DEDUCTION", "ACTIVE_INFORMATION"} & classes):
        missing.append("logical_or_active_information_problem")
    return tuple(missing)


def _one_shot_decision_scope(
    problem: ProblemIR, classes: frozenset[str]
) -> list[str]:
    missing: list[str] = []
    if "DECISION" not in classes:
        missing.append("decision_under_uncertainty")
    if problem.horizon is not Horizon.STATIC:
        missing.append("static_horizon")
    if "PLANNING" in classes:
        missing.append("sequential_planner_required")
    if "GAME" in classes:
        missing.append("strategic_solver_required")
    return missing


def _bayesian(
    problem: ProblemIR, classes: frozenset[str]
) -> tuple[str, ...]:
    missing = _one_shot_decision_scope(problem, classes)
    if problem.uncertainty is not UncertaintyKind.PROBABILISTIC:
        missing.append("probabilistic_uncertainty")
    return tuple(missing)


def _robust(
    problem: ProblemIR, classes: frozenset[str]
) -> tuple[str, ...]:
    missing = _one_shot_decision_scope(problem, classes)
    allowed = {
        UncertaintyKind.INTERVAL,
        UncertaintyKind.ADVERSARIAL,
        UncertaintyKind.UNKNOWN,
    }
    if problem.uncertainty not in allowed:
        missing.append("robust_uncertainty")
    return tuple(missing)


def _dynamic_programming(
    problem: ProblemIR, classes: frozenset[str]
) -> tuple[str, ...]:
    missing: list[str] = []
    if "PLANNING" not in classes:
        missing.append("planning_structure")
    if "GAME" in classes or len(problem.agents) != 1:
        missing.append("single_agent_planning")
    if problem.horizon is not Horizon.FINITE:
        missing.append("finite_horizon")
    if problem.model_status is not ModelStatus.KNOWN:
        missing.append("known_transition_model")
    return tuple(missing)


def _matrix_game(
    problem: ProblemIR, classes: frozenset[str]
) -> tuple[str, ...]:
    missing: list[str] = []
    if "GAME" not in classes:
        missing.append("multiple_strategic_agents")
    if len(problem.agents) != 2:
        missing.append("exactly_two_agents")
    if len(problem.actions) != 2:
        missing.append("two_actions_per_player")
    if problem.horizon is not Horizon.STATIC:
        missing.append("static_game")
    concept = (problem.solution_concept or "").casefold()
    if "zero-sum" not in concept and "zero sum" not in concept:
        missing.append("zero_sum_solution_concept")
    return tuple(missing)


def _monte_carlo(
    problem: ProblemIR, classes: frozenset[str]
) -> tuple[str, ...]:
    del classes
    missing: list[str] = []
    if problem.search_budget.rollouts <= 0:
        missing.append("positive_rollout_budget")
    if (
        problem.uncertainty is UncertaintyKind.NONE
        and problem.model_status is not ModelStatus.SIMULATOR
    ):
        missing.append("stochastic_source_or_simulator")
    return tuple(missing)


def _mcts(
    problem: ProblemIR, classes: frozenset[str]
) -> tuple[str, ...]:
    missing: list[str] = []
    if "PLANNING" not in classes:
        missing.append("planning_structure")
    if "GAME" in classes or len(problem.agents) != 1:
        missing.append("single_agent_planning")
    if problem.model_status is not ModelStatus.SIMULATOR:
        missing.append("simulator")
    if problem.search_budget.rollouts <= 0:
        missing.append("positive_rollout_budget")
    if problem.search_budget.max_depth <= 0:
        missing.append("positive_depth_budget")
    return tuple(missing)


def _muzero(
    problem: ProblemIR, classes: frozenset[str]
) -> tuple[str, ...]:
    missing: list[str] = []
    if "PLANNING" not in classes:
        missing.append("sequential_decision_problem")
    if "GAME" in classes or len(problem.agents) != 1:
        missing.append("single_agent_planning")
    if problem.model_status is not ModelStatus.LEARNABLE:
        missing.append("learnable_unknown_dynamics")
    if problem.search_budget.rollouts <= 0:
        missing.append("positive_rollout_budget")
    if problem.search_budget.max_depth <= 0:
        missing.append("positive_depth_budget")
    required_capabilities = {
        "interaction_data",
        "reward_signal",
        "neural_training",
    }
    missing.extend(
        sorted(required_capabilities - set(problem.capabilities))
    )
    return tuple(missing)


DEFAULT_SOLVERS: tuple[SolverCapability, ...] = (
    SolverCapability(
        "logic_exact",
        "exact",
        0,
        "Deduction, satisfiability, proof, countermodel, or "
        "active-information obstruction.",
        _logic_exact,
    ),
    SolverCapability(
        "bayesian_expected_utility",
        "exact-finite",
        1,
        "One-shot finite Bayesian decision under a declared probability model.",
        _bayesian,
    ),
    SolverCapability(
        "robust_minimax_regret",
        "exact-finite",
        2,
        "One-shot robust decision when a single trusted prior is unavailable.",
        _robust,
    ),
    SolverCapability(
        "finite_dynamic_programming",
        "exact-finite",
        2,
        "Single-agent finite-horizon planning with a known transition model.",
        _dynamic_programming,
    ),
    SolverCapability(
        "zero_sum_matrix_game",
        "exact-small",
        2,
        "Static two-agent, two-action zero-sum game with an explicit "
        "solution concept.",
        _matrix_game,
    ),
    SolverCapability(
        "monte_carlo_evaluation",
        "probabilistic-bound",
        4,
        "Seeded simulation support with explicit finite-sample uncertainty.",
        _monte_carlo,
    ),
    SolverCapability(
        "mcts",
        "approximate-search",
        5,
        "Single-agent Monte Carlo tree search when a deterministic simulator "
        "exists but exhaustive search is dominated.",
        _mcts,
    ),
    SolverCapability(
        "muzero",
        "learned-approximate-search",
        9,
        "Learn planning-relevant latent dynamics, policy, value, and reward "
        "before tree search.",
        _muzero,
    ),
)


def solver_index() -> dict[str, SolverCapability]:
    return {solver.name: solver for solver in DEFAULT_SOLVERS}
