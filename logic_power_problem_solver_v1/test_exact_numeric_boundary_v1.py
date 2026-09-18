from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from logic_power_problem_solver_v1.certificate import (
    build_certificate,
    verify_certificate,
)
from logic_power_problem_solver_v1.problem_ir import (
    Condition,
    ConditionKind,
    TerminalStatus,
)


class ExactNumericBoundaryTests(unittest.TestCase):
    def test_problem_metadata_rejects_float_and_unsafe_integer(self):
        with self.assertRaises(TypeError):
            Condition(
                "float",
                ConditionKind.FACT,
                "x",
                {"x": 0.5},
            )
        with self.assertRaises(ValueError):
            Condition(
                "large-int",
                ConditionKind.FACT,
                "x",
                {"x": 2**53},
            )

    def test_rehashed_float_certificate_is_rejected_by_python_and_node(self):
        with self.assertRaises(TypeError):
            build_certificate(
                problem_fingerprint="a" * 64,
                routing_fingerprint="b" * 64,
                status=TerminalStatus.SOLVED,
                result={"mean": 0.5},
                evidence={},
            )

        payload = {
            "problem_fingerprint": "a" * 64,
            "routing_fingerprint": "b" * 64,
            "status": TerminalStatus.SOLVED.value,
            "result": {"mean": 0.5},
            "evidence": {},
        }
        encoded = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
        certificate = {
            "schema": "logic-power-problem-solver/certificate/1",
            "payload": payload,
            "payload_sha256": hashlib.sha256(encoded).hexdigest(),
        }
        self.assertIn(
            "payload-canonical-json",
            verify_certificate(certificate),
        )

        verifier = Path(__file__).with_name(
            "verify_problem_solver_v1.js"
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "float.json"
            path.write_text(json.dumps(certificate))
            result = subprocess.run(
                ["node", str(verifier), str(path)],
                capture_output=True,
                text=True,
                check=False,
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("payload-canonical-json", result.stdout)


if __name__ == "__main__":
    unittest.main()
