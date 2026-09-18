"""Logic Power Problem Solver v1: typed routing before domain execution."""

from .certificate import build_certificate, verify_certificate
from .decision import (
    DecisionResult,
    expected_utility_decision,
    minimax_regret_decision,
    value_of_perfect_information,
)
from .games import ZeroSum2x2Result, solve_zero_sum_2x2
from .mcts import MCTSResult, plan_with_mcts
from .monte_carlo import MonteCarloEstimate, estimate_bounded_mean
from .planning import FiniteMDPPlan, MDPTransition, solve_finite_horizon_mdp
from .problem_ir import (
    Condition,
    ConditionKind,
    Horizon,
    ModelStatus,
    ProblemIR,
    SearchBudget,
    TerminalStatus,
    UncertaintyKind,
)
from .router import RoutingDecision, classify_problem, route_problem

__all__ = [
    "Condition",
    "ConditionKind",
    "DecisionResult",
    "FiniteMDPPlan",
    "Horizon",
    "MCTSResult",
    "MDPTransition",
    "ModelStatus",
    "MonteCarloEstimate",
    "ProblemIR",
    "RoutingDecision",
    "SearchBudget",
    "TerminalStatus",
    "UncertaintyKind",
    "ZeroSum2x2Result",
    "build_certificate",
    "classify_problem",
    "estimate_bounded_mean",
    "expected_utility_decision",
    "minimax_regret_decision",
    "plan_with_mcts",
    "route_problem",
    "solve_finite_horizon_mdp",
    "solve_zero_sum_2x2",
    "value_of_perfect_information",
    "verify_certificate",
]
