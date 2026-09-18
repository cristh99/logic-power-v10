from __future__ import annotations

import copy
import unittest
from fractions import Fraction

from logic_power_v10.active_discovery import (
    ActiveDiscoveryProblem,
    Experiment,
    MonitorStatus,
    make_impossible_demo,
    make_or_problem,
)
from logic_power_v10.certificate import (
    build_certificate,
    verify_certificate,
)
from logic_power_v10.eprocess import (
    demo_models,
    enumerate_adaptive_eprocess,
)


class LogicPowerV10Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.or8 = make_or_problem(8)
        cls.policy = cls.or8.optimal_policy()
        cls.exact_certificate = build_certificate(
            cls.or8, "or_8_exact"
        )

    def test_monitor_four_states(self) -> None:
        self.assertEqual(
            self.or8.monitor([]), MonitorStatus.INCONSISTENT
        )
        self.assertEqual(
            self.or8.monitor(["00000000"]), MonitorStatus.FALSE
        )
        self.assertEqual(
            self.or8.monitor(["10000000"]), MonitorStatus.TRUE
        )
        self.assertEqual(
            self.or8.monitor(["00000000", "10000000"]),
            MonitorStatus.UNKNOWN,
        )

    def test_or8_has_255_conflicting_pairs(self) -> None:
        self.assertEqual(len(self.or8.conflict_pairs()), 255)

    def test_exact_basis_contains_every_bit(self) -> None:
        basis = self.or8.exact_fixed_basis()
        self.assertIsNotNone(basis)
        self.assertEqual(
            [experiment.name for experiment in basis],
            [f"bit_{index}" for index in range(8)],
        )

    def test_every_or8_bit_is_necessary(self) -> None:
        basis = self.or8.exact_fixed_basis()
        assert basis is not None
        conflicts = self.or8.conflict_pairs()
        for omitted in basis:
            remaining = [
                experiment
                for experiment in basis
                if experiment != omitted
            ]
            self.assertTrue(
                any(
                    not any(
                        experiment.observations[left]
                        != experiment.observations[right]
                        for experiment in remaining
                    )
                    for left, right in conflicts
                )
            )

    def test_optimal_policy_costs(self) -> None:
        self.assertTrue(self.policy["exact"])
        self.assertEqual(self.policy["worst_cost"], [8, 1])
        self.assertEqual(
            self.policy["expected_cost"], [255, 128]
        )

    def test_adaptive_advantage_formula(self) -> None:
        for bits in range(1, 7):
            policy = make_or_problem(bits).optimal_policy()
            self.assertEqual(
                Fraction(*policy["expected_cost"]),
                Fraction(2) - Fraction(1, 2 ** (bits - 1)),
            )

    def test_cegis_builds_a_separating_basis(self) -> None:
        basis = self.or8.cegis_basis()
        self.assertIsNotNone(basis)
        self.assertEqual(
            {experiment.name for experiment in basis},
            {f"bit_{index}" for index in range(8)},
        )

    def test_impossible_problem_emits_obstruction(self) -> None:
        problem = make_impossible_demo()
        self.assertEqual(
            problem.obstruction(),
            ("false_world", "true_world"),
        )
        self.assertIsNone(problem.exact_fixed_basis())
        self.assertFalse(problem.optimal_policy()["exact"])

    def test_certificate_is_deterministic_and_valid(self) -> None:
        rebuilt = build_certificate(self.or8, "or_8_exact")
        self.assertEqual(self.exact_certificate, rebuilt)
        self.assertEqual(verify_certificate(rebuilt), [])

    def test_tampered_certificate_is_rejected(self) -> None:
        altered = copy.deepcopy(self.exact_certificate)
        altered["payload"]["problem"]["hypotheses"][0][
            "property"
        ] = True
        self.assertIn(
            "payload-hash", verify_certificate(altered)
        )

    def test_eprocess_expectation_and_partition(self) -> None:
        sensors, null, alt, policy = demo_models()
        result = enumerate_adaptive_eprocess(
            4, sensors, null, alt, policy, Fraction(9)
        )
        self.assertEqual(result["expectation"], [1, 1])
        self.assertEqual(result["terminal_mass"], [1, 1])

    def test_fail_closed_validation(self) -> None:
        with self.assertRaises(ValueError):
            ActiveDiscoveryProblem(
                ("a", "b"),
                {"a": False, "b": True},
                (
                    Experiment(
                        "bad", Fraction(1), {"a": "x"}
                    ),
                ),
            )


if __name__ == "__main__":
    unittest.main()
