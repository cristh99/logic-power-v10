from __future__ import annotations

import json
from fractions import Fraction
from pathlib import Path
from typing import Mapping

from logic_power_v10.active_discovery import ActiveDiscoveryProblem
from logic_power_v10.certificate import (
    build_certificate,
    verify_certificate,
)

from .capital_allocation import (
    make_capital_allocation_problem,
    make_hidden_liability_obstruction,
)
from .casebook import FINANCE_CASEBOOK


ROOT = Path(__file__).resolve().parents[1]


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        )
        + "\n",
        encoding="utf-8",
    )


def _summarize_exact_problem(
    problem: ActiveDiscoveryProblem,
    certificate: Mapping[str, object],
) -> dict[str, object]:
    basis = problem.exact_fixed_basis()
    if basis is None:
        raise AssertionError("exact finance case unexpectedly impossible")
    fixed_cost = sum(
        (experiment.cost for experiment in basis), Fraction(0)
    )
    policy = problem.optimal_policy()
    expected_cost = Fraction(*policy["expected_cost"])
    reduction = Fraction(1) - expected_cost / fixed_cost
    positive_worlds = sum(problem.property_values.values())
    return {
        "hypotheses": len(problem.hypotheses),
        "positive_worlds": positive_worlds,
        "negative_worlds": len(problem.hypotheses) - positive_worlds,
        "conflict_pairs": len(problem.conflict_pairs()),
        "fixed_basis": [experiment.name for experiment in basis],
        "fixed_basis_cost": [fixed_cost.numerator, fixed_cost.denominator],
        "adaptive_worst_cost": policy["worst_cost"],
        "adaptive_expected_cost": policy["expected_cost"],
        "adaptive_reduction": [reduction.numerator, reduction.denominator],
        "root_experiment": policy["tree"].get("experiment"),
        "certificate_sha256": certificate["sha256"],
    }


def main() -> None:
    exact_problems = {
        "capital_allocation": make_capital_allocation_problem(),
        **{case.name: case.make_problem() for case in FINANCE_CASEBOOK},
    }
    impossible_problem = make_hidden_liability_obstruction()

    certificates: dict[str, dict[str, object]] = {}
    verification: dict[str, list[str]] = {}
    exact_summaries: dict[str, dict[str, object]] = {}

    for name, problem in exact_problems.items():
        certificate = build_certificate(
            problem, f"finance_{name}_exact"
        )
        certificates[name] = certificate
        verification[name] = verify_certificate(certificate)
        exact_summaries[name] = _summarize_exact_problem(
            problem, certificate
        )
        _write_json(
            ROOT / "certificates" / f"finance_{name}_exact.json",
            certificate,
        )

    impossible_certificate = build_certificate(
        impossible_problem, "finance_hidden_liability_impossible"
    )
    certificates["hidden_liability"] = impossible_certificate
    verification["hidden_liability"] = verify_certificate(
        impossible_certificate
    )
    _write_json(
        ROOT
        / "certificates"
        / "finance_hidden_liability_impossible.json",
        impossible_certificate,
    )

    if any(verification.values()):
        raise SystemExit(f"certificate verification failed: {verification}")

    summary = {
        "schema": "finance-logic-v10/summary/2",
        "suite": {
            "exact_cases": len(exact_problems),
            "obstruction_cases": 1,
            "hypotheses": sum(
                item["hypotheses"] for item in exact_summaries.values()
            ),
            "conflict_pairs": sum(
                item["conflict_pairs"]
                for item in exact_summaries.values()
            ),
            "certificates": len(certificates),
        },
        "exact_cases": exact_summaries,
        "hidden_liability": {
            "exact": impossible_problem.optimal_policy()["exact"],
            "status": impossible_problem.optimal_policy()["tree"]["status"],
            "obstruction": list(
                impossible_problem.obstruction() or ()
            ),
            "certificate_sha256": impossible_certificate["sha256"],
        },
        "verification": verification,
    }
    _write_json(
        ROOT / "reports" / "finance_logic_v10_summary.json",
        summary,
    )
    print(
        json.dumps(
            summary,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        )
    )


if __name__ == "__main__":
    main()
