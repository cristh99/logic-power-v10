from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from logic_power_v10.active_discovery import (
    make_impossible_demo,
    make_or_problem,
)
from logic_power_v10.certificate import build_certificate

ROOT = Path(__file__).resolve().parents[1]


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "logic_power_v10", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )


class CliV10Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tmp = tempfile.TemporaryDirectory()
        cls.dir = Path(cls.tmp.name)
        certificates = {
            "exact": build_certificate(make_or_problem(8), "or_8_exact"),
            "impossible": build_certificate(
                make_impossible_demo(), "flat_sensor_impossible"
            ),
        }
        tampered = copy.deepcopy(certificates["exact"])
        tampered["payload"]["problem"]["hypotheses"][0]["property"] = True
        certificates["tampered"] = tampered
        cls.paths = {}
        for name, certificate in certificates.items():
            path = cls.dir / f"{name}.json"
            path.write_text(
                json.dumps(certificate, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            cls.paths[name] = path

    @classmethod
    def tearDownClass(cls) -> None:
        cls.tmp.cleanup()

    def test_verify_accepts_exact_certificate(self) -> None:
        completed = run_cli("verify", str(self.paths["exact"]))
        self.assertEqual(completed.returncode, 0)
        self.assertEqual(
            json.loads(completed.stdout), {"errors": [], "valid": True}
        )

    def test_verify_accepts_impossible_certificate(self) -> None:
        completed = run_cli("verify", str(self.paths["impossible"]))
        self.assertEqual(completed.returncode, 0)
        self.assertEqual(
            json.loads(completed.stdout), {"errors": [], "valid": True}
        )

    def test_verify_rejects_tampered_certificate(self) -> None:
        completed = run_cli("verify", str(self.paths["tampered"]))
        self.assertEqual(completed.returncode, 1)
        self.assertEqual(
            json.loads(completed.stdout),
            {"errors": ["payload-hash"], "valid": False},
        )

    def test_usage_error(self) -> None:
        for args in ((), ("verify",), ("bogus", "x")):
            completed = run_cli(*args)
            self.assertEqual(completed.returncode, 2)
            self.assertIn("usage:", completed.stderr)

    def test_help_prints_usage(self) -> None:
        completed = run_cli("--help")
        self.assertEqual(completed.returncode, 0)
        self.assertIn(
            "python -m logic_power_v10 verify", completed.stdout
        )


if __name__ == "__main__":
    unittest.main()
