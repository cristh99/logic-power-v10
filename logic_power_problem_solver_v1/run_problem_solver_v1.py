"""Deterministic vertical-slice demonstration for Problem Solver v1."""
from __future__ import annotations

import json
from fractions import Fraction
from pathlib import Path
from typing import Any

from .certificate import build_certificate
from .decision import expected_utility_decision, value_of_perfect_information
from .games import solve_zero_sum_2x2
from .mcts import plan_with_mcts
from .planning import MDPTransition, solve_finite_horizon_mdp
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
from .router import route_problem


def _fraction(value: Fraction) -> list[int]:
    return [value.numerator, value.denominator]


def _route_data(problem: ProblemIR) -> tuple[dict[str, Any], str]:
    route = route_problem(problem)
    return route.canonical_data(), route.fingerprint()


def _certificate_case(
    *,
    problem: ProblemIR,
    status: TerminalStatus,
    result: dict[str, Any],
    evidence: dict[str, Any],
) -> dict[str, Any]:
    route, route_hash = _route_data(problem)
    certificate = build_certificate(
        problem_fingerprint=problem.fingerprint(),
        routing_fingerprint=route_hash,
        status=status,
        result=result,
        evidence=evidence,
    )
    return {
        "status": status.value,
        "problem_fingerprint": problem.fingerprint(),
        "route": route,
        "result": result,
        "certificate": certificate,
    }


def _planning_fixture() -> tuple[
    tuple[str, ...],
    dict[str, tuple[str, ...]],
    dict[tuple[str, str], tuple[MDPTransition, ...]],
]:
    states = ("root", "middle", "terminal")
    actions = {
        "root": ("explore", "safe"),
        "middle": ("bad", "good"),
        "terminal": (),
    }
    transitions = {
        ("root", "safe"): (
            MDPTransition("terminal", Fraction(1), Fraction(4)),
        ),
        ("root", "explore"): (
            MDPTransition("middle", Fraction(1), Fraction(0)),
        ),
        ("middle", "good"): (
            MDPTransition("terminal", Fraction(1), Fraction(10)),
        ),
        ("middle", "bad"): (
            MDPTransition("terminal", Fraction(1), Fraction(-10)),
        ),
    }
    return states, actions, transitions


def build_demo_report() -> dict[str, Any]:
    decision_problem = ProblemIR(
        problem_id="weather-decision",
        states=("rain", "dry"),
        initial_belief=("rain", "dry"),
        goal="choose action with maximum declared expected utility",
        conditions=(
            Condition(
                "prior",
                ConditionKind.FACT,
                "P(rain)=1/4; P(dry)=3/4",
            ),
            Condition(
                "proof",
                ConditionKind.EVIDENCE_REQUIREMENT,
                "exact rational replay",
            ),
        ),
        actions=("umbrella", "none"),
        experiments=(),
        agents=("decision_maker",),
        horizon=Horizon.STATIC,
        uncertainty=UncertaintyKind.PROBABILISTIC,
        model_status=ModelStatus.KNOWN,
        objective="maximize expected utility",
        capabilities=(
            "bayesian_expected_utility",
            "robust_minimax_regret",
        ),
        verifiers=("python", "node"),
    )
    prior = {"rain": Fraction(1, 4), "dry": Fraction(3, 4)}
    utilities = {
        "umbrella": {
            "rain": Fraction(8),
            "dry": Fraction(2),
        },
        "none": {
            "rain": Fraction(-6),
            "dry": Fraction(5),
        },
    }
    decision = expected_utility_decision(prior, utilities)
    vpi = value_of_perfect_information(prior, utilities)
    decision_result = {
        "action": decision.action,
        "expected_utility": _fraction(decision.score),
        "value_of_perfect_information": _fraction(vpi),
    }
    decision_case = _certificate_case(
        problem=decision_problem,
        status=TerminalStatus.SOLVED,
        result=decision_result,
        evidence={
            "criterion": decision.criterion,
            "scores": {
                name: _fraction(value)
                for name, value in sorted(decision.scores.items())
            },
        },
    )

    game_problem = ProblemIR(
        problem_id="matching-pennies",
        states=("payoff_matrix_known",),
        initial_belief=("payoff_matrix_known",),
        goal="compute the zero-sum equilibrium",
        conditions=(
            Condition(
                "zero_sum",
                ConditionKind.FACT,
                "row payoff equals negative column payoff",
            ),
            Condition(
                "exact",
                ConditionKind.EVIDENCE_REQUIREMENT,
                "exact rational equilibrium",
            ),
        ),
        actions=("heads", "tails"),
        experiments=(),
        agents=("row", "column"),
        horizon=Horizon.STATIC,
        uncertainty=UncertaintyKind.ADVERSARIAL,
        model_status=ModelStatus.KNOWN,
        objective="row maximizes and column minimizes",
        capabilities=(
            "zero_sum_matrix_game",
            "robust_minimax_regret",
        ),
        verifiers=("python", "node"),
        solution_concept="zero-sum Nash equilibrium",
    )
    game = solve_zero_sum_2x2(
        (
            (Fraction(1), Fraction(-1)),
            (Fraction(-1), Fraction(1)),
        )
    )
    game_result = {
        "kind": game.kind,
        "row_strategy": [
            _fraction(value) for value in game.row_strategy
        ],
        "column_strategy": [
            _fraction(value) for value in game.column_strategy
        ],
        "value": _fraction(game.value),
    }
    game_case = _certificate_case(
        problem=game_problem,
        status=TerminalStatus.SOLVED,
        result=game_result,
        evidence={"solution_concept": game_problem.solution_concept},
    )

    states, actions_by_state, transitions = _planning_fixture()
    planning_problem = ProblemIR(
        problem_id="finite-planning-oracle",
        states=states,
        initial_belief=("root",),
        goal="reach the highest exact finite-horizon return",
        conditions=(
            Condition(
                "known_model",
                ConditionKind.FACT,
                "all transition probabilities and rewards are exact",
            ),
            Condition(
                "horizon",
                ConditionKind.BUDGET,
                "two actions of depth",
            ),
        ),
        actions=("explore", "safe", "bad", "good"),
        experiments=(),
        agents=("planner",),
        horizon=Horizon.FINITE,
        uncertainty=UncertaintyKind.NONE,
        model_status=ModelStatus.KNOWN,
        objective="maximize exact total reward",
        capabilities=("finite_dynamic_programming",),
        verifiers=("python", "node"),
        search_budget=SearchBudget(max_depth=2),
    )
    exact_plan = solve_finite_horizon_mdp(
        states=states,
        actions_by_state=actions_by_state,
        transitions=transitions,
        terminal_states=("terminal",),
        start_state="root",
        horizon=2,
    )
    planning_result = {
        "action": exact_plan.start_action,
        "value": _fraction(exact_plan.start_value),
        "horizon": exact_plan.horizon,
        "policy": dict(exact_plan.policy),
    }
    planning_case = _certificate_case(
        problem=planning_problem,
        status=TerminalStatus.SOLVED,
        result=planning_result,
        evidence={
            "method": "exact_backward_dynamic_programming",
            "discount": _fraction(exact_plan.discount),
        },
    )

    def available_actions(state: str) -> tuple[str, ...]:
        return actions_by_state[state]

    def deterministic_step(
        state: str,
        action: str,
    ) -> tuple[str, Fraction, bool]:
        outcome = transitions[(state, action)][0]
        return (
            outcome.next_state,
            outcome.reward,
            outcome.next_state == "terminal",
        )

    mcts_problem = ProblemIR(
        problem_id="mcts-against-exact-oracle",
        states=states,
        initial_belief=("root",),
        goal="select the same root action as the exact finite oracle",
        conditions=(
            Condition(
                "simulator",
                ConditionKind.FACT,
                "deterministic simulator available",
            ),
            Condition(
                "search_budget",
                ConditionKind.BUDGET,
                "500 seeded rollouts; depth two",
            ),
            Condition(
                "oracle",
                ConditionKind.EVIDENCE_REQUIREMENT,
                "compare against exact dynamic programming",
            ),
        ),
        actions=("explore", "safe", "bad", "good"),
        experiments=(),
        agents=("planner",),
        horizon=Horizon.FINITE,
        uncertainty=UncertaintyKind.NONE,
        model_status=ModelStatus.SIMULATOR,
        objective="maximize sampled total reward",
        capabilities=("mcts",),
        verifiers=("python", "node"),
        search_budget=SearchBudget(rollouts=500, max_depth=2),
    )
    mcts = plan_with_mcts(
        start_state="root",
        actions=available_actions,
        step=deterministic_step,
        horizon=2,
        rollouts=500,
        seed=17,
    )
    mcts_result = {
        "action": mcts.action,
        "oracle_action": exact_plan.start_action,
        "matches_oracle": mcts.action == exact_plan.start_action,
        "root_visits": mcts.root_visits,
        "action_visits": dict(mcts.action_visits),
        "action_mean_returns": {
            action: _fraction(value)
            for action, value in sorted(
                mcts.action_mean_returns.items()
            )
        },
        "rollouts": mcts.rollouts,
        "seed": mcts.seed,
        "horizon": mcts.horizon,
    }
    if not mcts_result["matches_oracle"]:
        raise AssertionError("MCTS failed the exact-oracle promotion gate")
    mcts_case = _certificate_case(
        problem=mcts_problem,
        status=TerminalStatus.SOLVED,
        result=mcts_result,
        evidence={
            "method": "seeded_uct_deterministic_simulator",
            "oracle_value": _fraction(exact_plan.start_value),
        },
    )

    muzero_problem = ProblemIR(
        problem_id="learned-planning-gate",
        states=("latent_dynamics_unknown",),
        initial_belief=("latent_dynamics_unknown",),
        goal="select a learned planning method",
        conditions=(
            Condition(
                "budget",
                ConditionKind.BUDGET,
                "500 rollouts; depth 10",
            ),
            Condition(
                "proof",
                ConditionKind.EVIDENCE_REQUIREMENT,
                "sealed baseline comparison",
            ),
        ),
        actions=("act",),
        experiments=(),
        agents=("learner",),
        horizon=Horizon.FINITE,
        uncertainty=UncertaintyKind.PROBABILISTIC,
        model_status=ModelStatus.LEARNABLE,
        objective="maximize long-run reward",
        capabilities=("muzero",),
        verifiers=("python",),
        search_budget=SearchBudget(rollouts=500, max_depth=10),
    )
    muzero_route_obj = route_problem(muzero_problem)
    missing = sorted(
        muzero_route_obj.rejected_solvers.get("muzero", ())
    )
    muzero_result = {
        "status": TerminalStatus.BLOCKED.value,
        "missing": missing,
        "selected_solver": muzero_route_obj.selected_solver,
    }
    muzero_certificate = build_certificate(
        problem_fingerprint=muzero_problem.fingerprint(),
        routing_fingerprint=muzero_route_obj.fingerprint(),
        status=TerminalStatus.BLOCKED,
        result=muzero_result,
        evidence={
            "rule": "no learned planner without declared prerequisites"
        },
    )
    muzero_case = {
        **muzero_result,
        "problem_fingerprint": muzero_problem.fingerprint(),
        "route": muzero_route_obj.canonical_data(),
        "result": muzero_result,
        "certificate": muzero_certificate,
    }

    return {
        "schema": "logic-power-problem-solver/demo-report/1",
        "cases": {
            "decision": decision_case,
            "game": game_case,
            "planning": planning_case,
            "mcts": mcts_case,
            "muzero_gate": muzero_case,
        },
    }


def main() -> int:
    report = build_demo_report()
    reports = Path("reports")
    certificates = Path("certificates")
    reports.mkdir(parents=True, exist_ok=True)
    certificates.mkdir(parents=True, exist_ok=True)
    report_path = reports / "problem_solver_v1.json"
    report_path.write_text(
        json.dumps(
            report,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        + "\n"
    )
    for name, case in report["cases"].items():
        (
            certificates / f"problem_solver_v1_{name}.json"
        ).write_text(
            json.dumps(
                case["certificate"],
                indent=2,
                sort_keys=True,
            )
            + "\n"
        )
    print(
        json.dumps(
            {
                "report": str(report_path),
                "cases": {
                    name: case["status"]
                    for name, case in report["cases"].items()
                },
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
