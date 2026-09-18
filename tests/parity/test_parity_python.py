from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

from logic_power_v10.certificate import canonical_json, digest_payload

PARITY = Path(__file__).resolve().parent
ROOT = PARITY.parents[1]
FIXTURE = json.loads(
    (PARITY / "canonical_cases.json").read_text(encoding="utf-8")
)


class CanonicalParityTests(unittest.TestCase):
    def test_fixture_is_well_formed(self) -> None:
        names = [case["name"] for case in FIXTURE["cases"]]
        self.assertEqual(len(names), len(set(names)))
        self.assertLessEqual(
            set(FIXTURE["known_divergences"]), set(names)
        )

    def test_canonical_json_matches_fixture(self) -> None:
        for case in FIXTURE["cases"]:
            with self.subTest(case=case["name"]):
                self.assertEqual(
                    canonical_json(case["value"]), case["canonical"]
                )
                self.assertEqual(
                    digest_payload(case["value"]), case["sha256"]
                )

    def test_known_divergences_recompute(self) -> None:
        divergences = FIXTURE["known_divergences"]
        for case in FIXTURE["cases"]:
            node = divergences.get(case["name"])
            with self.subTest(case=case["name"]):
                if node is None:
                    continue
                self.assertNotEqual(
                    node["node_canonical"], case["canonical"]
                )
                self.assertTrue(node["reason"])

    def test_tampered_certificate_rejected(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "logic_power_v10.verify_logic_power_v10",
                str(PARITY / "logic_power_v10_exact_tampered.json"),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 1)
        self.assertEqual(
            json.loads(completed.stdout),
            {"errors": ["payload-hash"], "valid": False},
        )


if __name__ == "__main__":
    unittest.main()
