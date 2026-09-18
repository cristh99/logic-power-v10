"""Deterministic hybrid-problem classifier and minimum-method router."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from .problem_ir import Horizon, ModelStatus, ProblemIR, UncertaintyKind
from .solver_registry import DEFAULT_SOLVERS


@dataclass(frozen=True)
class RoutingDecision:
    problem_classes: tuple[str, ...]
    selected_solver: str | None
    eligible_solvers: tuple[str, ...]
    rejected_solvers: dict[str, tuple[str, ...]]
    trace: tuple[str, ...]

    def canonical_data(self) -> dict[str, object]:
        return {
            "problem_classes": list(self.problem_classes),
            "selected_solver": self.selected_solver,
            "eligible_solvers": list(self.eligible_solvers),
            "rejected_solvers": {
                name: list(self.rejected_solvers[name])
                for name in sorted(self.rejected_solvers)
            },
            "trace": list(self.trace),
        }

    def fingerprint(self) -> str:
        payload = json.dumps(
            self.canonical_data(),
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()


def classify_problem(
    problem: ProblemIR,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    classes: set[str] = set()
    trace: list[str] = []

    if len(problem.agents) > 1:
        classes.add("GAME")
        trace.append("multiple agents => GAME")
    if problem.actions and problem.horizon is not Horizon.STATIC:
        classes.add("PLANNING")
        trace.append("actions plus non-static horizon => PLANNING")
    if problem.uncertainty is not UncertaintyKind.NONE:
        classes.add("DECISION")
        trace.append(
            f"uncertainty={problem.uncertainty.value} => DECISION"
        )
    if (
        problem.model_status is ModelStatus.SIMULATOR
        and problem.search_budget.rollouts > 0
    ):
        classes.add("SIMULATION_SEARCH")
        trace.append("simulator plus rollouts => SIMULATION_SEARCH")
    if problem.model_status is ModelStatus.LEARNABLE:
        classes.add("LEARNING")
        trace.append("learnable dynamics => LEARNING")
    if problem.experiments:
        classes.add("ACTIVE_INFORMATION")
        trace.append("declared experiments => ACTIVE_INFORMATION")
    if any(
        condition.kind.value == "EVIDENCE_REQUIREMENT"
        for condition in problem.conditions
    ):
        classes.add("VERIFICATION")
        trace.append("evidence requirement => VERIFICATION")
    if not classes or classes == {"VERIFICATION"}:
        classes.add("DEDUCTION")
        trace.append(
            "no sequential, strategic, or stochastic structure "
            "=> DEDUCTION"
        )

    return tuple(sorted(classes)), tuple(trace)


def _selection_order(classes: frozenset[str]) -> tuple[str, ...]:
    order: list[str] = []
    if "GAME" in classes:
        order.append("zero_sum_matrix_game")
    if "LEARNING" in classes:
        order.append("muzero")
    if "SIMULATION_SEARCH" in classes:
        order.append("mcts")
    if "PLANNING" in classes:
        order.append("finite_dynamic_programming")
    if "DECISION" in classes:
        order.extend(
            ("bayesian_expected_utility", "robust_minimax_regret")
        )
    if "ACTIVE_INFORMATION" in classes:
        order.append("logic_exact")
    # Monte Carlo is a supporting estimator in v1, not a primary planner.
    order.append("logic_exact")
    seen: set[str] = set()
    return tuple(
        item for item in order if not (item in seen or seen.add(item))
    )


def route_problem(problem: ProblemIR) -> RoutingDecision:
    problem_classes, trace = classify_problem(problem)
    class_set = frozenset(problem_classes)
    available = set(problem.capabilities)
    eligible: list[str] = []
    rejected: dict[str, tuple[str, ...]] = {}

    for solver in DEFAULT_SOLVERS:
        if solver.name not in available:
            continue
        reasons = solver.eligibility(problem, class_set)
        if reasons:
            rejected[solver.name] = reasons
        else:
            eligible.append(solver.name)

    selected: str | None = None
    for candidate in _selection_order(class_set):
        if candidate in eligible:
            selected = candidate
            break

    routing_trace = list(trace)
    routing_trace.append(
        f"selected={selected}" if selected is not None else "selected=None"
    )
    for name in sorted(rejected):
        routing_trace.append(
            f"rejected={name}:{','.join(rejected[name])}"
        )

    return RoutingDecision(
        problem_classes=problem_classes,
        selected_solver=selected,
        eligible_solvers=tuple(sorted(eligible)),
        rejected_solvers=rejected,
        trace=tuple(routing_trace),
    )
