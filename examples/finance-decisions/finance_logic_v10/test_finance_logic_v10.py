from __future__ import annotations

import copy
import unittest
from fractions import Fraction

from logic_power_v10.certificate import (
    build_certificate,
    verify_certificate,
)

from finance_logic_v10.capital_allocation import (
    make_capital_allocation_problem,
    make_hidden_liability_obstruction,
)
from finance_logic_v10.casebook import (
    FINANCE_CASEBOOK,
    BinaryFinanceCase,
    summarize_case,
)


class FinanceLogicV10Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.problem = make_capital_allocation_problem()
        cls.certificate = build_certificate(
            cls.problem, "finance_capital_allocation_exact"
        )

    def test_capital_allocation_universe(self) -> None:
        self.assertEqual(len(self.problem.hypotheses), 32)
        self.assertEqual(
            sum(self.problem.property_values.values()), 11
        )
        self.assertEqual(len(self.problem.conflict_pairs()), 231)

    def test_every_due_diligence_axis_is_required(self) -> None:
        basis = self.problem.exact_fixed_basis()
        self.assertIsNotNone(basis)
        assert basis is not None
        self.assertEqual(
            [experiment.name for experiment in basis],
            [
                "committed_financing_term_sheet",
                "fixed_price_vendor_quote",
                "signed_customer_contracts",
                "terminal_reinvestment_audit",
                "working_capital_quality_audit",
            ],
        )
        self.assertEqual(
            sum(
                (experiment.cost for experiment in basis),
                Fraction(0),
            ),
            Fraction(10),
        )

    def test_optimal_adaptive_policy(self) -> None:
        policy = self.problem.optimal_policy()
        self.assertTrue(policy["exact"])
        self.assertEqual(policy["worst_cost"], [10, 1])
        self.assertEqual(policy["expected_cost"], [25, 4])
        self.assertEqual(
            policy["tree"]["experiment"],
            "signed_customer_contracts",
        )
        self.assertEqual(
            Fraction(1) - Fraction(25, 4) / Fraction(10),
            Fraction(3, 8),
        )

    def test_certificate_is_deterministic_and_valid(self) -> None:
        rebuilt = build_certificate(
            self.problem, "finance_capital_allocation_exact"
        )
        self.assertEqual(self.certificate, rebuilt)
        self.assertEqual(verify_certificate(rebuilt), [])

    def test_tampered_certificate_is_rejected(self) -> None:
        altered = copy.deepcopy(self.certificate)
        altered["payload"]["problem"]["hypotheses"][0][
            "property"
        ] = not altered["payload"]["problem"]["hypotheses"][0][
            "property"
        ]
        self.assertIn(
            "payload-hash", verify_certificate(altered)
        )

    def test_hidden_liability_fails_closed(self) -> None:
        problem = make_hidden_liability_obstruction()
        self.assertEqual(
            problem.obstruction(),
            ("clean_balance_sheet", "hidden_tax_claim"),
        )
        self.assertIsNone(problem.exact_fixed_basis())
        policy = problem.optimal_policy()
        self.assertFalse(policy["exact"])
        self.assertEqual(
            policy["tree"]["status"], "IMPOSSIBLE"
        )
        certificate = build_certificate(
            problem, "finance_hidden_liability_impossible"
        )
        self.assertEqual(verify_certificate(certificate), [])

    def test_casebook_contract_validation(self) -> None:
        with self.assertRaises(ValueError):
            BinaryFinanceCase(
                name="bad",
                axes=(("risk", ("good", "bad")),),
                adverse_values={"risk": "missing"},
                charges={"risk": 1},
                threshold=0,
                experiments=(("audit", Fraction(1), "risk"),),
                positive_label="YES",
                negative_label="NO",
            )

    def test_casebook_all_axes_are_material(self) -> None:
        for case in FINANCE_CASEBOOK:
            with self.subTest(case=case.name):
                problem = case.make_problem()
                basis = problem.exact_fixed_basis()
                self.assertIsNotNone(basis)
                assert basis is not None
                self.assertEqual(len(problem.hypotheses), 32)
                self.assertEqual(len(basis), 5)
                self.assertEqual(
                    {experiment.name for experiment in basis},
                    {name for name, _, _ in case.experiments},
                )

    def test_casebook_exact_metrics(self) -> None:
        expected = {
            "credit_underwriting": {
                "positive_worlds": 14,
                "conflict_pairs": 252,
                "fixed_basis_cost": [9, 1],
                "adaptive_expected_cost": [23, 4],
                "adaptive_reduction": [13, 36],
                "root_experiment": "cash_flow_quality_audit",
            },
            "liquidity_survival": {
                "positive_worlds": 14,
                "conflict_pairs": 252,
                "fixed_basis_cost": [7, 1],
                "adaptive_expected_cost": [35, 8],
                "adaptive_reduction": [3, 8],
                "root_experiment": "committed_revolver_confirmation",
            },
            "portfolio_mandate": {
                "positive_worlds": 14,
                "conflict_pairs": 252,
                "fixed_basis_cost": [10, 1],
                "adaptive_expected_cost": [115, 16],
                "adaptive_reduction": [9, 32],
                "root_experiment": "forward_return_assumption_audit",
            },
            "bank_stress_resilience": {
                "positive_worlds": 15,
                "conflict_pairs": 255,
                "fixed_basis_cost": [9, 1],
                "adaptive_expected_cost": [13, 2],
                "adaptive_reduction": [5, 18],
                "root_experiment": "deposit_concentration_runoff_study",
            },
        }
        for case in FINANCE_CASEBOOK:
            with self.subTest(case=case.name):
                summary = summarize_case(case)
                for key, value in expected[case.name].items():
                    self.assertEqual(summary[key], value)

    def test_casebook_certificates_replay(self) -> None:
        for case in FINANCE_CASEBOOK:
            with self.subTest(case=case.name):
                certificate = build_certificate(
                    case.make_problem(), f"finance_{case.name}_exact"
                )
                self.assertEqual(verify_certificate(certificate), [])


if __name__ == "__main__":
    unittest.main()
