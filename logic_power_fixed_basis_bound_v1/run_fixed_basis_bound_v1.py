from __future__ import annotations

import copy
import json
from fractions import Fraction
from pathlib import Path

from logic_power_v10.active_discovery import (
    ActiveDiscoveryProblem,
    Experiment,
    make_impossible_demo,
    make_or_problem,
)
from logic_power_v10.certificate import build_certificate

from logic_power_fixed_basis_bound_v1.certificate import (
    build_bound_certificate,
    digest_payload,
)

ROOT = Path(__file__).resolve().parents[1]
CERTIFICATES = ROOT / "certificates"
REPORTS = ROOT / "reports"

CANONICAL_EXACT_SHA256 = (
    "7a05fde469d38ebed19e22838b16776f3bfcec462791d275069e38b2dbea3e7c"
)
CANONICAL_IMPOSSIBLE_SHA256 = (
    "0367df5ca9d49c523f87ca1f39c5ebbea4d591231f642ff72f584c012a01b602"
)


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def make_gap_triangle() -> ActiveDiscoveryProblem:
    """Four-hypothesis instance with an integrality gap.

    Conflict pairs are (h1,h4), (h2,h4), (h3,h4); each unit-cost
    experiment separates exactly two of them, so the minimum basis
    costs 2 while the greedy dual reaches only 1.
    """
    return ActiveDiscoveryProblem(
        ("h1", "h2", "h3", "h4"),
        {"h1": False, "h2": False, "h3": False, "h4": True},
        (
            Experiment(
                name="e12",
                cost=Fraction(1),
                observations={
                    "h1": "x",
                    "h2": "x",
                    "h3": "y",
                    "h4": "y",
                },
            ),
            Experiment(
                name="e13",
                cost=Fraction(1),
                observations={
                    "h1": "x",
                    "h2": "y",
                    "h3": "x",
                    "h4": "y",
                },
            ),
            Experiment(
                name="e23",
                cost=Fraction(1),
                observations={
                    "h1": "y",
                    "h2": "x",
                    "h3": "x",
                    "h4": "y",
                },
            ),
        ),
    )


def _summary(
    certificate: dict[str, object],
    problem: ActiveDiscoveryProblem,
) -> dict[str, object]:
    payload = certificate["payload"]
    problem_data = payload["problem"]
    analysis = payload["analysis"]
    dual = analysis["dual"]
    forced = analysis["forced_experiments"]
    return {
        "case": payload["case"],
        "sha256": certificate["sha256"],
        "parent_certificate_sha256": payload[
            "parent_certificate_sha256"
        ],
        "hypotheses": len(problem_data["hypotheses"]),
        "experiments": len(problem_data["experiments"]),
        "conflict_pairs": len(problem.conflict_pairs()),
        "basis_cost": analysis["fixed_basis_cost"],
        "dual_value": None if dual is None else dual["value"],
        "dual_support": None if dual is None else len(dual["weights"]),
        "forced_count": None if forced is None else len(forced),
        "tight": analysis["tight"],
        "obstruction": analysis["obstruction"],
    }


def main() -> None:
    or8 = make_or_problem(8)
    core_exact = build_certificate(or8, "or_8_exact")
    if core_exact["sha256"] != CANONICAL_EXACT_SHA256:
        raise SystemExit(
            "canonical or_8_exact hash mismatch: "
            f"{core_exact['sha256']} != {CANONICAL_EXACT_SHA256}"
        )
    bound_or8 = build_bound_certificate(
        or8,
        "or_8_exact",
        parent_certificate_sha256=core_exact["sha256"],
    )

    gap = make_gap_triangle()
    bound_gap = build_bound_certificate(gap, "gap_triangle")

    impossible = make_impossible_demo()
    core_impossible = build_certificate(
        impossible, "flat_sensor_impossible"
    )
    if core_impossible["sha256"] != CANONICAL_IMPOSSIBLE_SHA256:
        raise SystemExit(
            "canonical flat_sensor_impossible hash mismatch: "
            f"{core_impossible['sha256']} "
            f"!= {CANONICAL_IMPOSSIBLE_SHA256}"
        )
    bound_impossible = build_bound_certificate(
        impossible,
        "flat_sensor_impossible",
        parent_certificate_sha256=core_impossible["sha256"],
    )

    tampered = copy.deepcopy(bound_or8)
    tampered["payload"]["analysis"]["dual"]["weights"][0][1] = [2, 1]

    forged = copy.deepcopy(bound_or8)
    forged["payload"]["analysis"]["dual"]["weights"][0][1] = [2, 1]
    forged["sha256"] = digest_payload(forged["payload"])

    write_json(
        CERTIFICATES / "fixed_basis_bound_or8.json", bound_or8
    )
    write_json(
        CERTIFICATES / "fixed_basis_bound_gap.json", bound_gap
    )
    write_json(
        CERTIFICATES / "fixed_basis_bound_impossible.json",
        bound_impossible,
    )
    write_json(
        CERTIFICATES / "fixed_basis_bound_tampered.json", tampered
    )
    write_json(
        CERTIFICATES / "fixed_basis_bound_forged.json", forged
    )

    report = {
        "schema": "logic-power-v10/fixed-basis-bound-report/1",
        "certificates": [
            _summary(bound_or8, or8),
            _summary(bound_gap, gap),
            _summary(bound_impossible, impossible),
        ],
    }
    write_json(REPORTS / "fixed_basis_bound_v1.json", report)


if __name__ == "__main__":
    main()
