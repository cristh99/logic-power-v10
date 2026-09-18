from __future__ import annotations

import copy
import json
import subprocess
import tempfile
import unittest
from fractions import Fraction
from pathlib import Path

from logic_power_problem_solver_v1.certificate import (
    build_certificate,
    verify_certificate,
)
from logic_power_problem_solver_v1.decision import (
    expected_utility_decision,
    minimax_regret_decision,
    value_of_perfect_information,
)
from logic_power_problem_solver_v1.games import solve_zero_sum_2x2
from logic_power_problem_solver_v1.monte_carlo import estimate_bounded_mean
from logic_power_problem_solver_v1.problem_ir import (
    Condition,
    ConditionKind,
    Horizon,
    ModelStatus,
    ProblemIR,
    SearchBudget,
    TerminalStatus,
    UncertaintyKind,
)
from logic_power_problem_solver_v1.router import route_problem
from logic_power_problem_solver_v1.run_problem_solver_v1 import (
    build_demo_report,
)


class ProblemIRTests(unittest.TestCase):
    def make_base(self, **overrides):
        data = dict(
            problem_id="demo",
            states=("s0", "s1"),
            initial_belief=("s0", "s1"),
            goal="choose",
            conditions=(
                Condition(
                    "public_only",
                    ConditionKind.HARD_CONSTRAINT,
                    "public routes only",
                ),
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
            objective="satisfy goal",
            capabilities=("logic_exact",),
            verifiers=("python",),
            search_budget=SearchBudget(),
        )
        data.update(overrides)
        return ProblemIR(**data)

    def test_fail_closed_belief_must_be_subset(self):
        with self.assertRaises(ValueError):
            self.make_base(initial_belief=("s0", "ghost"))

    def test_canonical_hash_is_order_invariant_where_semantics_are_sets(self):
        left = self.make_base(
            states=("s1", "s0"),
            initial_belief=("s1", "s0"),
            actions=("a1", "a0"),
            capabilities=("logic_exact", "bayes"),
        )
        right = self.make_base(
            states=("s0", "s1"),
            initial_belief=("s0", "s1"),
            actions=("a0", "a1"),
            capabilities=("bayes", "logic_exact"),
        )
        self.assertEqual(left.fingerprint(), right.fingerprint())

    def test_problem_ir_freezes_mutable_inputs(self):
        states = ["s0", "s1"]
        metadata = {"source": ["official", 1]}
        condition = Condition(
            "source",
            ConditionKind.FACT,
            "official source exists",
            metadata,
        )
        problem = self.make_base(states=states, conditions=[condition])
        before = problem.fingerprint()

        states.append("ghost")
        metadata["source"].append("tampered")

        self.assertEqual(problem.states, ("s0", "s1"))
        self.assertEqual(problem.fingerprint(), before)
        with self.assertRaises(TypeError):
            problem.conditions[0].metadata["new"] = "value"

    def test_problem_ir_rejects_untyped_enums_and_float_metadata(self):
        with self.assertRaises(TypeError):
            self.make_base(horizon="STATIC")
        with self.assertRaises(TypeError):
            Condition(
                "float",
                ConditionKind.FACT,
                "x",
                {"x": 1.25},
            )

    def test_router_selects_decision_theory_for_probabilistic_static_choice(
        self,
    ):
        problem = self.make_base(
            uncertainty=UncertaintyKind.PROBABILISTIC,
            capabilities=("bayesian_expected_utility", "logic_exact"),
        )
        route = route_problem(problem)
        self.assertIn("DECISION", route.problem_classes)
        self.assertEqual(
            route.selected_solver,
            "bayesian_expected_utility",
        )

    def test_router_marks_mcts_eligible_with_simulator_and_budget(self):
        problem = self.make_base(
            horizon=Horizon.FINITE,
            model_status=ModelStatus.SIMULATOR,
            search_budget=SearchBudget(rollouts=1000, max_depth=20),
            capabilities=("mcts", "finite_dynamic_programming"),
        )
        route = route_problem(problem)
        self.assertIn("PLANNING", route.problem_classes)
        self.assertIn("SIMULATION_SEARCH", route.problem_classes)
        self.assertIn("mcts", route.eligible_solvers)

    def test_router_does_not_use_logic_exact_as_a_planning_fallback(self):
        problem = self.make_base(
            horizon=Horizon.FINITE,
            model_status=ModelStatus.UNKNOWN,
            capabilities=("logic_exact",),
        )
        route = route_problem(problem)
        self.assertIsNone(route.selected_solver)
        self.assertIn("logic_exact", route.rejected_solvers)

    def test_router_does_not_use_one_shot_bayes_for_sequential_planning(
        self,
    ):
        problem = self.make_base(
            horizon=Horizon.FINITE,
            uncertainty=UncertaintyKind.PROBABILISTIC,
            model_status=ModelStatus.UNKNOWN,
            capabilities=("bayesian_expected_utility",),
        )
        route = route_problem(problem)
        self.assertIsNone(route.selected_solver)
        self.assertIn(
            "bayesian_expected_utility",
            route.rejected_solvers,
        )
        self.assertIn(
            "static_horizon",
            route.rejected_solvers["bayesian_expected_utility"],
        )

    def test_router_rejects_matrix_game_outside_exact_kernel_scope(self):
        problem = self.make_base(
            agents=("row", "column", "third"),
            uncertainty=UncertaintyKind.ADVERSARIAL,
            capabilities=("zero_sum_matrix_game",),
            solution_concept="general Nash equilibrium",
        )
        route = route_problem(problem)
        self.assertIsNone(route.selected_solver)
        self.assertIn(
            "exactly_two_agents",
            route.rejected_solvers["zero_sum_matrix_game"],
        )
        self.assertIn(
            "zero_sum_solution_concept",
            route.rejected_solvers["zero_sum_matrix_game"],
        )

    def test_router_rejects_muzero_without_learning_preconditions(self):
        problem = self.make_base(
            horizon=Horizon.FINITE,
            model_status=ModelStatus.LEARNABLE,
            search_budget=SearchBudget(rollouts=500, max_depth=10),
            capabilities=("muzero",),
        )
        route = route_problem(problem)
        self.assertNotIn("muzero", route.eligible_solvers)
        self.assertIn("muzero", route.rejected_solvers)
        self.assertIn(
            "interaction_data",
            route.rejected_solvers["muzero"],
        )

    def test_router_allows_muzero_only_when_all_preconditions_are_declared(
        self,
    ):
        problem = self.make_base(
            horizon=Horizon.FINITE,
            model_status=ModelStatus.LEARNABLE,
            uncertainty=UncertaintyKind.PROBABILISTIC,
            search_budget=SearchBudget(rollouts=500, max_depth=10),
            capabilities=(
                "muzero",
                "interaction_data",
                "reward_signal",
                "neural_training",
            ),
        )
        route = route_problem(problem)
        self.assertIn("muzero", route.eligible_solvers)

    def test_router_rejects_muzero_without_positive_depth(self):
        problem = self.make_base(
            horizon=Horizon.FINITE,
            model_status=ModelStatus.LEARNABLE,
            uncertainty=UncertaintyKind.PROBABILISTIC,
            search_budget=SearchBudget(rollouts=500, max_depth=0),
            capabilities=(
                "muzero",
                "interaction_data",
                "reward_signal",
                "neural_training",
            ),
        )
        route = route_problem(problem)
        self.assertNotIn("muzero", route.eligible_solvers)
        self.assertIn(
            "positive_depth_budget",
            route.rejected_solvers["muzero"],
        )


class DecisionTests(unittest.TestCase):
    def setUp(self):
        self.prior = {
            "rain": Fraction(1, 4),
            "dry": Fraction(3, 4),
        }
        self.utilities = {
            "umbrella": {
                "rain": Fraction(8),
                "dry": Fraction(2),
            },
            "none": {
                "rain": Fraction(-6),
                "dry": Fraction(5),
            },
        }

    def test_expected_utility_decision(self):
        result = expected_utility_decision(self.prior, self.utilities)
        self.assertEqual(result.action, "umbrella")
        self.assertEqual(result.score, Fraction(7, 2))

    def test_minimax_regret_decision(self):
        result = minimax_regret_decision(self.utilities)
        self.assertEqual(result.action, "umbrella")
        self.assertEqual(result.score, Fraction(3))

    def test_value_of_perfect_information(self):
        value = value_of_perfect_information(
            self.prior,
            self.utilities,
        )
        self.assertEqual(value, Fraction(9, 4))

    def test_monte_carlo_is_seeded_and_bounded(self):
        sampler = lambda rng: 1.0 if rng.random() < 0.5 else 0.0
        first = estimate_bounded_mean(
            sampler,
            2000,
            lower=0.0,
            upper=1.0,
            confidence=0.99,
            seed=7,
        )
        second = estimate_bounded_mean(
            sampler,
            2000,
            lower=0.0,
            upper=1.0,
            confidence=0.99,
            seed=7,
        )
        self.assertEqual(first, second)
        self.assertLess(first.radius, 0.04)
        self.assertLessEqual(first.lower_bound, 0.5)
        self.assertGreaterEqual(first.upper_bound, 0.5)


class GameTheoryTests(unittest.TestCase):
    def test_detects_pure_saddle_point(self):
        result = solve_zero_sum_2x2(
            (
                (Fraction(3), Fraction(1)),
                (Fraction(2), Fraction(2)),
            )
        )
        self.assertEqual(result.kind, "PURE")
        self.assertEqual(
            result.row_strategy,
            (Fraction(0), Fraction(1)),
        )
        self.assertEqual(
            result.column_strategy,
            (Fraction(0), Fraction(1)),
        )
        self.assertEqual(result.value, Fraction(2))

    def test_solves_matching_pennies_mixed_equilibrium(self):
        result = solve_zero_sum_2x2(
            (
                (Fraction(1), Fraction(-1)),
                (Fraction(-1), Fraction(1)),
            )
        )
        self.assertEqual(result.kind, "MIXED")
        self.assertEqual(
            result.row_strategy,
            (Fraction(1, 2), Fraction(1, 2)),
        )
        self.assertEqual(
            result.column_strategy,
            (Fraction(1, 2), Fraction(1, 2)),
        )
        self.assertEqual(result.value, Fraction(0))


class DemoReportTests(unittest.TestCase):
    def test_demo_report_is_deterministic_and_fail_closed(self):
        first = build_demo_report()
        second = build_demo_report()
        self.assertEqual(first, second)
        self.assertEqual(
            first["cases"]["decision"]["route"]["selected_solver"],
            "bayesian_expected_utility",
        )
        self.assertEqual(
            first["cases"]["game"]["route"]["selected_solver"],
            "zero_sum_matrix_game",
        )
        self.assertEqual(
            first["cases"]["muzero_gate"]["status"],
            "BLOCKED",
        )
        self.assertIn(
            "interaction_data",
            first["cases"]["muzero_gate"]["missing"],
        )


class CertificateTests(unittest.TestCase):
    def test_certificate_rejects_tampering(self):
        cert = build_certificate(
            problem_fingerprint="a" * 64,
            routing_fingerprint="b" * 64,
            status=TerminalStatus.SOLVED,
            result={"action": "umbrella"},
            evidence={"expected_utility": [7, 2]},
        )
        self.assertEqual(verify_certificate(cert), [])
        altered = copy.deepcopy(cert)
        altered["payload"]["result"]["action"] = "none"
        self.assertEqual(
            verify_certificate(altered),
            ["payload-hash"],
        )

    def test_python_verifier_rejects_non_hex_fingerprints(self):
        cert = build_certificate(
            problem_fingerprint="a" * 64,
            routing_fingerprint="b" * 64,
            status=TerminalStatus.SOLVED,
            result={"ok": True},
            evidence={},
        )
        cert["payload"]["problem_fingerprint"] = "z" * 64
        import hashlib

        payload = json.dumps(
            cert["payload"],
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
        cert["payload_sha256"] = hashlib.sha256(payload).hexdigest()
        self.assertIn(
            "problem_fingerprint",
            verify_certificate(cert),
        )

    def test_independent_node_verifier(self):
        cert = build_certificate(
            problem_fingerprint="c" * 64,
            routing_fingerprint="d" * 64,
            status=TerminalStatus.SOLVED,
            result={"value": [1, 2]},
            evidence={"method": "exact"},
        )
        verifier = Path(__file__).with_name(
            "verify_problem_solver_v1.js"
        )
        with tempfile.TemporaryDirectory() as tmp:
            valid_path = Path(tmp) / "valid.json"
            valid_path.write_text(json.dumps(cert))
            valid = subprocess.run(
                ["node", str(verifier), str(valid_path)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(valid.returncode, 0, valid.stderr)
            altered = copy.deepcopy(cert)
            altered["payload"]["result"]["value"] = [9, 10]
            bad_path = Path(tmp) / "bad.json"
            bad_path.write_text(json.dumps(altered))
            invalid = subprocess.run(
                ["node", str(verifier), str(bad_path)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(invalid.returncode, 0)


if __name__ == "__main__":
    unittest.main()
