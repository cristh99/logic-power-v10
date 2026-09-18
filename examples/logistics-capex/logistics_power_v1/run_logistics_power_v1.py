from __future__ import annotations

import copy
import hashlib
import json
from fractions import Fraction
from pathlib import Path

from logic_power_v10.certificate import (
    build_certificate,
    canonical_json,
    verify_certificate,
)

from .capex_gate import (
    HYPOTHESIS_SEMANTICS,
    make_capex_gate_problem,
)

ROOT = Path(__file__).resolve().parents[1]
CERTIFICATES = ROOT / "certificates"
REPORTS = ROOT / "reports"


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _fraction(value: object) -> Fraction:
    if not isinstance(value, list) or len(value) != 2:
        raise ValueError("fraction must be [numerator, denominator]")
    return Fraction(value[0], value[1])


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_manifest(paths: list[Path]) -> Path:
    manifest = REPORTS / "logistics_power_v1_evidence.sha256"
    lines = [
        f"{_sha256(path)}  {path.relative_to(ROOT)}"
        for path in sorted(paths, key=lambda item: str(item.relative_to(ROOT)))
    ]
    manifest.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return manifest


def main() -> None:
    exact_problem = make_capex_gate_problem(include_supplier_trace=True)
    impossible_problem = make_capex_gate_problem(
        include_supplier_trace=False
    )

    exact_certificate = build_certificate(
        exact_problem, "logistics_capex_gate_exact"
    )
    impossible_certificate = build_certificate(
        impossible_problem, "logistics_capex_gate_missing_supplier_sensor"
    )
    tampered_certificate = copy.deepcopy(exact_certificate)
    tampered_certificate["payload"]["problem"]["hypotheses"][0][
        "property"
    ] = True

    for certificate in (exact_certificate, impossible_certificate):
        errors = verify_certificate(certificate)
        if errors:
            raise RuntimeError(f"certificate verification failed: {errors}")
    tampered_errors = verify_certificate(tampered_certificate)
    if "payload-hash" not in tampered_errors:
        raise RuntimeError(
            "negative control failed: tampered certificate was not rejected"
        )

    exact_path = (
        CERTIFICATES / "logistics_power_v1_capex_exact.json"
    )
    impossible_path = (
        CERTIFICATES
        / "logistics_power_v1_capex_impossible.json"
    )
    tampered_path = (
        CERTIFICATES / "logistics_power_v1_capex_tampered.json"
    )
    _write_json(exact_path, exact_certificate)
    _write_json(impossible_path, impossible_certificate)
    _write_json(tampered_path, tampered_certificate)

    exact_analysis = exact_certificate["payload"]["analysis"]
    impossible_analysis = impossible_certificate["payload"]["analysis"]
    fixed_cost = _fraction(exact_analysis["fixed_basis_cost"])
    expected_cost = _fraction(
        exact_analysis["policy"]["expected_cost"]
    )
    expected_reduction = (fixed_cost - expected_cost) / fixed_cost

    report = {
        "schema": "logistics-power-v1/report/1",
        "status": "PASS_FINITE_DECLARED_DOMAIN",
        "logic_source": {
            "engine": "Logic Power v10",
            "private_pr": 53,
            "verified_head": (
                "ba10d0edc7eb20d499d0481fda2537e782b6efb2"
            ),
        },
        "decision": (
            "Authorize candidate-station capacity expansion only when "
            "capacity shortage is present and neither rework nor supplier "
            "instability is the limiting mechanism."
        ),
        "exact_case": {
            "hypotheses": len(HYPOTHESIS_SEMANTICS),
            "conflict_pairs": len(exact_analysis["conflict_pairs"]),
            "minimum_fixed_basis": exact_analysis["fixed_basis"],
            "minimum_fixed_cost": exact_analysis["fixed_basis_cost"],
            "adaptive_worst_cost": exact_analysis["policy"][
                "worst_cost"
            ],
            "adaptive_expected_cost": exact_analysis["policy"][
                "expected_cost"
            ],
            "adaptive_root_experiment": exact_analysis["policy"][
                "tree"
            ]["experiment"],
            "expected_cost_reduction": [
                expected_reduction.numerator,
                expected_reduction.denominator,
            ],
        },
        "impossible_case": {
            "removed_experiment": "supplier_continuity_trace",
            "obstruction": impossible_analysis["obstruction"],
            "meaning": (
                "A true capacity-only world and a supplier-instability "
                "world require opposite decisions but are observationally "
                "identical without a supplier continuity trace."
            ),
        },
        "negative_control": {
            "tampered_certificate_rejected": True,
            "python_error": "payload-hash",
        },
        "hypothesis_semantics": HYPOTHESIS_SEMANTICS,
        "certificates": {
            "exact": {
                "path": str(exact_path.relative_to(ROOT)),
                "sha256": exact_certificate["sha256"],
            },
            "impossible": {
                "path": str(impossible_path.relative_to(ROOT)),
                "sha256": impossible_certificate["sha256"],
            },
            "tampered": {
                "path": str(tampered_path.relative_to(ROOT)),
                "expected": "REJECT",
            },
        },
        "scope": (
            "finite deterministic logistics hypotheses, declared probes, "
            "exact rational costs and priors; advisory only"
        ),
        "promotion_boundary": (
            "This proves the compiler and synthetic gate, not real-world "
            "causal validity or production readiness. Promotion requires a "
            "versioned operational dataset, a predeclared pilot, guardrails, "
            "and before/after service-cost-risk evidence."
        ),
    }

    report_path = REPORTS / "logistics_power_v1.json"
    canonical_path = REPORTS / "logistics_power_v1.canonical.json"
    _write_json(report_path, report)
    canonical_path.write_text(
        canonical_json(report) + "\n", encoding="utf-8"
    )

    _write_manifest(
        [
            ROOT / "README_logistics_power_v1.md",
            ROOT / ".github/workflows/logistics-power-v1.yml",
            ROOT / "logistics_power_v1/__init__.py",
            ROOT / "logistics_power_v1/capex_gate.py",
            ROOT / "logistics_power_v1/run_logistics_power_v1.py",
            ROOT / "logistics_power_v1/test_logistics_power_v1.py",
            exact_path,
            impossible_path,
            tampered_path,
            report_path,
            canonical_path,
        ]
    )


if __name__ == "__main__":
    main()
