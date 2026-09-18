from __future__ import annotations

import copy
import unittest
from fractions import Fraction

from logic_power_v10.certificate import (
    build_certificate,
    verify_certificate,
)

from logistics_power_v1.capex_gate import (
    HYPOTHESIS_SEMANTICS,
    make_capex_gate_problem,
)


class LogisticsPowerV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.problem = make_capex_gate_problem(
            include_supplier_trace=True
        )
        cls.policy = cls.problem.optimal_policy()
        cls.certificate = build_certificate(
            cls.problem, "logistics_capex_gate_exact"
        )

    def test_exactly_one_world_authorizes_capex(self) -> None:
        approved = [
            hypothesis
            for hypothesis in self.problem.hypotheses
            if self.problem.property_values[hypothesis]
        ]
        self.assertEqual(approved, ["c1_q0_s0"])

    def test_hypothesis_space_is_complete(self) -> None:
        self.assertEqual(len(HYPOTHESIS_SEMANTICS), 8)
        self.assertEqual(len(self.problem.conflict_pairs()), 7)

    def test_minimum_fixed_basis_requires_all_three_probes(self) -> None:
        basis = self.problem.exact_fixed_basis()
        self.assertIsNotNone(basis)
        assert basis is not None
        self.assertEqual(
            [experiment.name for experiment in basis],
            [
                "capacity_stress_pilot",
                "first_pass_yield_audit",
                "supplier_continuity_trace",
            ],
        )
        self.assertEqual(
            sum(
                (experiment.cost for experiment in basis),
                Fraction(0),
            ),
            Fraction(6),
        )

    def test_optimal_policy_tests_cheap_invalidators_first(self) -> None:
        self.assertTrue(self.policy["exact"])
        self.assertEqual(self.policy["worst_cost"], [6, 1])
        self.assertEqual(self.policy["expected_cost"], [5, 2])

        root = self.policy["tree"]
        self.assertEqual(root["experiment"], "first_pass_yield_audit")
        self.assertEqual(root["children"]["rework_excess"]["status"], "FALSE")

        supplier_node = root["children"]["first_pass_yield_ok"]
        self.assertEqual(
            supplier_node["experiment"],
            "supplier_continuity_trace",
        )
        self.assertEqual(
            supplier_node["children"]["supplier_unstable"]["status"],
            "FALSE",
        )
        self.assertEqual(
            supplier_node["children"]["supplier_stable"][
                "experiment"
            ],
            "capacity_stress_pilot",
        )

    def test_adaptive_policy_reduces_expected_probe_cost(self) -> None:
        fixed = Fraction(6)
        adaptive = Fraction(*self.policy["expected_cost"])
        self.assertEqual((fixed - adaptive) / fixed, Fraction(7, 12))

    def test_missing_supplier_trace_emits_exact_obstruction(self) -> None:
        impossible = make_capex_gate_problem(
            include_supplier_trace=False
        )
        self.assertEqual(
            impossible.obstruction(),
            ("c1_q0_s0", "c1_q0_s1"),
        )
        self.assertIsNone(impossible.exact_fixed_basis())
        self.assertFalse(impossible.optimal_policy()["exact"])

    def test_supplier_trace_repairs_the_obstruction(self) -> None:
        self.assertIsNone(self.problem.obstruction())
        self.assertIsNotNone(self.problem.exact_fixed_basis())

    def test_certificate_is_deterministic_and_valid(self) -> None:
        rebuilt = build_certificate(
            self.problem, "logistics_capex_gate_exact"
        )
        self.assertEqual(rebuilt, self.certificate)
        self.assertEqual(verify_certificate(rebuilt), [])

    def test_tampered_certificate_is_rejected(self) -> None:
        tampered = copy.deepcopy(self.certificate)
        tampered["payload"]["problem"]["hypotheses"][0][
            "property"
        ] = True
        self.assertIn("payload-hash", verify_certificate(tampered))


if __name__ == "__main__":
    unittest.main()
