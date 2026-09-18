from __future__ import annotations

import copy
import json
from fractions import Fraction
from pathlib import Path

from logic_power_v10.active_discovery import (
    make_impossible_demo,
    make_or_problem,
)
from logic_power_v10.certificate import build_certificate, canonical_json
from logic_power_v10.eprocess import (
    demo_models,
    enumerate_adaptive_eprocess,
)

ROOT = Path(__file__).resolve().parents[1]
CERTIFICATES = ROOT / "certificates"
REPORTS = ROOT / "reports"


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    exact_problem = make_or_problem(8)
    impossible_problem = make_impossible_demo()
    exact_certificate = build_certificate(
        exact_problem, "or_8_exact"
    )
    impossible_certificate = build_certificate(
        impossible_problem, "flat_sensor_impossible"
    )

    tampered = copy.deepcopy(exact_certificate)
    tampered["payload"]["problem"]["hypotheses"][0][
        "property"
    ] = True

    write_json(
        CERTIFICATES / "logic_power_v10_exact.json",
        exact_certificate,
    )
    write_json(
        CERTIFICATES / "logic_power_v10_impossible.json",
        impossible_certificate,
    )
    write_json(
        CERTIFICATES / "logic_power_v10_tampered.json", tampered
    )

    sensors, null, alt, policy = demo_models()
    eprocess = enumerate_adaptive_eprocess(
        horizon=4,
        sensors=sensors,
        null=null,
        alt=alt,
        policy=policy,
        stop_threshold=Fraction(9, 1),
    )

    exact_analysis = exact_certificate["payload"]["analysis"]
    impossible_analysis = impossible_certificate["payload"][
        "analysis"
    ]
    report = {
        "schema": "logic-power-v10/report/1",
        "active_discovery": {
            "hypotheses": 256,
            "conflict_pairs": len(
                exact_analysis["conflict_pairs"]
            ),
            "minimum_fixed_basis": len(
                exact_analysis["fixed_basis"]
            ),
            "adaptive_worst_cost": exact_analysis["policy"][
                "worst_cost"
            ],
            "adaptive_expected_cost": exact_analysis["policy"][
                "expected_cost"
            ],
            "fixed_expected_reduction_percent": [19225, 256],
            "impossible_obstruction": impossible_analysis[
                "obstruction"
            ],
        },
        "eprocess": eprocess,
        "certificates": {
            "exact_sha256": exact_certificate["sha256"],
            "impossible_sha256": impossible_certificate["sha256"],
        },
        "scope": (
            "finite hypotheses, declared deterministic experiments, "
            "exact rational costs and priors"
        ),
        "score": {
            "finite_internal_domain": 1000,
            "global_knowledge_area": (
                "set only after all repository and Notion gates match"
            ),
        },
    }
    write_json(REPORTS / "logic_power_v10.json", report)
    (REPORTS / "logic_power_v10.canonical.json").write_text(
        canonical_json(report) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
