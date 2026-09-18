from __future__ import annotations

import copy
import unittest
from fractions import Fraction

from logic_power_v10.active_discovery import (
    make_impossible_demo,
    make_or_problem,
)
from logic_power_v10.certificate import build_certificate

from logic_power_fixed_basis_bound_v1.bounds import (
    dual_lower_bound,
    separates,
)
from logic_power_fixed_basis_bound_v1.certificate import (
    build_bound_certificate,
    digest_payload,
    verify_bound_certificate,
)
from logic_power_fixed_basis_bound_v1.run_fixed_basis_bound_v1 import (
    make_gap_triangle,
)


class FixedBasisBoundTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.or8 = make_or_problem(8)
        cls.or8_certificate = build_bound_certificate(
            cls.or8, "or_8_exact"
        )
        cls.analysis = cls.or8_certificate["payload"]["analysis"]

    def test_or8_dual_is_tight_with_unit_support(self) -> None:
        self.assertEqual(self.analysis["dual"]["value"], [8, 1])
        self.assertTrue(self.analysis["tight"])
        self.assertEqual(
            self.analysis["dual"]["weights"],
            [
                [["00000000", format(1 << index, "08b")], [1, 1]]
                for index in range(8)
            ],
        )
        self.assertEqual(
            [
                entry["experiment"]
                for entry in self.analysis["forced_experiments"]
            ],
            [f"bit_{index}" for index in range(8)],
        )

    def test_or8_dual_feasibility_recomputed(self) -> None:
        weights = {
            tuple(pair): Fraction(*weight)
            for pair, weight in self.analysis["dual"]["weights"]
        }
        for experiment in self.or8.experiments:
            load = sum(
                (
                    weight
                    for pair, weight in weights.items()
                    if separates(experiment, pair)
                ),
                Fraction(0),
            )
            self.assertLessEqual(load, experiment.cost)

    def test_impossible_certificate(self) -> None:
        certificate = build_bound_certificate(
            make_impossible_demo(), "flat_sensor_impossible"
        )
        analysis = certificate["payload"]["analysis"]
        self.assertEqual(
            analysis["obstruction"], ["false_world", "true_world"]
        )
        for field in (
            "fixed_basis",
            "fixed_basis_cost",
            "forced_experiments",
            "dual",
            "tight",
        ):
            self.assertIsNone(analysis[field])
        self.assertEqual(verify_bound_certificate(certificate), [])

    def test_gap_triangle_integrality_gap(self) -> None:
        certificate = build_bound_certificate(
            make_gap_triangle(), "gap_triangle"
        )
        analysis = certificate["payload"]["analysis"]
        self.assertEqual(analysis["fixed_basis_cost"], [2, 1])
        self.assertEqual(analysis["dual"]["value"], [1, 1])
        self.assertFalse(analysis["tight"])
        self.assertEqual(verify_bound_certificate(certificate), [])

    def test_certificate_is_deterministic_and_valid(self) -> None:
        rebuilt = build_bound_certificate(self.or8, "or_8_exact")
        self.assertEqual(self.or8_certificate, rebuilt)
        self.assertEqual(verify_bound_certificate(rebuilt), [])

    def test_tampered_certificate_is_rejected(self) -> None:
        altered = copy.deepcopy(self.or8_certificate)
        altered["payload"]["analysis"]["dual"]["weights"][0][1] = [
            2,
            1,
        ]
        self.assertEqual(
            ["payload-hash"], verify_bound_certificate(altered)
        )

    def test_forged_dual_is_infeasible(self) -> None:
        altered = copy.deepcopy(self.or8_certificate)
        altered["payload"]["analysis"]["dual"]["weights"][0][1] = [
            2,
            1,
        ]
        altered["sha256"] = digest_payload(altered["payload"])
        self.assertIn(
            "dual-feasible", verify_bound_certificate(altered)
        )

    def test_flipped_tight_flag_is_rejected(self) -> None:
        altered = copy.deepcopy(self.or8_certificate)
        altered["payload"]["analysis"]["tight"] = False
        altered["sha256"] = digest_payload(altered["payload"])
        self.assertIn(
            "tight-flag", verify_bound_certificate(altered)
        )

    def test_basis_with_missing_experiment_is_rejected(self) -> None:
        altered = copy.deepcopy(self.or8_certificate)
        altered["payload"]["analysis"]["fixed_basis"] = altered[
            "payload"
        ]["analysis"]["fixed_basis"][:-1]
        altered["sha256"] = digest_payload(altered["payload"])
        self.assertIn(
            "basis-cover", verify_bound_certificate(altered)
        )

    def test_core_certificate_hashes_are_stable(self) -> None:
        self.assertEqual(
            build_certificate(make_or_problem(8), "or_8_exact")[
                "sha256"
            ],
            "7a05fde469d38ebed19e22838b16776f3bfcec462791d275069e38b2dbea3e7c",
        )
        self.assertEqual(
            build_certificate(
                make_impossible_demo(), "flat_sensor_impossible"
            )["sha256"],
            "0367df5ca9d49c523f87ca1f39c5ebbea4d591231f642ff72f584c012a01b602",
        )


if __name__ == "__main__":
    unittest.main()
