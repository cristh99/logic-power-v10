from __future__ import annotations

import unittest

from logic_power_problem_solver_v1.problem_ir import (
    Condition,
    ConditionKind,
    Horizon,
    ModelStatus,
    ProblemIR,
    SearchBudget,
    UncertaintyKind,
)
from logic_power_problem_solver_v1.router import route_problem
from logic_power_problem_solver_v1.run_problem_solver_v1 import build_demo_report


def make_problem(**overrides) -> ProblemIR:
    data = dict(
        problem_id="routing-integration",
        states=("s0", "s1"),
        initial_belief=("s0", "s1"),
        goal="choose a valid primary method",
        conditions=(
            Condition(
                "proof",
                ConditionKind.EVIDENCE_REQUIREMENT,
                "certificate required",
            ),
        ),
        actions=("a0", "a1"),
        experiments=(),
        agents=("solver",),
        horizon=Horizon.STATIC,
        uncertainty=UncertaintyKind.NONE,
        model_status=ModelStatus.KNOWN,
        objective="satisfy the declared goal",
        capabilities=("logic_exact",),
        verifiers=("python", "node"),
        search_budget=SearchBudget(),
    )
    data.update(overrides)
    return ProblemIR(**data)


class RoutingHardeningIntegrationTests(unittest.TestCase):
    def test_router_does_not_select_monte_carlo_as_planner(self):
        problem = make_problem(
            horizon=Horizon.FINITE,
            uncertainty=UncertaintyKind.PROBABILISTIC,
            model_status=ModelStatus.UNKNOWN,
            search_budget=SearchBudget(rollouts=1000, max_depth=5),
            capabilities=("monte_carlo_evaluation",),
        )
        route = route_problem(problem)
        self.assertIn("monte_carlo_evaluation", route.eligible_solvers)
        self.assertIsNone(route.selected_solver)

    def test_router_rejects_single_agent_mcts_for_game(self):
        problem = make_problem(
            agents=("row", "column"),
            horizon=Horizon.FINITE,
            uncertainty=UncertaintyKind.ADVERSARIAL,
            model_status=ModelStatus.SIMULATOR,
            search_budget=SearchBudget(rollouts=1000, max_depth=5),
            capabilities=("mcts",),
            solution_concept="zero-sum extensive-form game",
        )
        route = route_problem(problem)
        self.assertIsNone(route.selected_solver)
        self.assertIn(
            "single_agent_planning",
            route.rejected_solvers["mcts"],
        )

    def test_demo_routes_exact_planning_and_mcts(self):
        report = build_demo_report()
        self.assertEqual(
            report["cases"]["planning"]["route"]["selected_solver"],
            "finite_dynamic_programming",
        )
        self.assertEqual(
            report["cases"]["planning"]["result"]["action"],
            "explore",
        )
        self.assertEqual(
            report["cases"]["mcts"]["route"]["selected_solver"],
            "mcts",
        )
        self.assertTrue(
            report["cases"]["mcts"]["result"]["matches_oracle"]
        )


if __name__ == "__main__":
    unittest.main()
