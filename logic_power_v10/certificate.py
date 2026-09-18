from __future__ import annotations

import hashlib
import json
from fractions import Fraction
from typing import Any, Mapping

from .active_discovery import ActiveDiscoveryProblem, Experiment


def canonical_json(value: object) -> str:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )


def digest_payload(payload: object) -> str:
    return hashlib.sha256(
        canonical_json(payload).encode("utf-8")
    ).hexdigest()


def _fraction(value: object) -> Fraction:
    if not isinstance(value, list) or len(value) != 2:
        raise ValueError("fraction must be [numerator, denominator]")
    numerator, denominator = value
    if (
        not isinstance(numerator, int)
        or not isinstance(denominator, int)
        or denominator <= 0
    ):
        raise ValueError("invalid fraction")
    return Fraction(numerator, denominator)


def problem_from_data(
    data: Mapping[str, Any],
) -> ActiveDiscoveryProblem:
    hypotheses_data = data.get("hypotheses")
    experiments_data = data.get("experiments")
    if not isinstance(hypotheses_data, list) or not isinstance(
        experiments_data, list
    ):
        raise ValueError("malformed problem")
    hypotheses = tuple(item["id"] for item in hypotheses_data)
    properties = {
        item["id"]: bool(item["property"]) for item in hypotheses_data
    }
    prior = {
        item["id"]: _fraction(item["prior"])
        for item in hypotheses_data
    }
    experiments = tuple(
        Experiment(
            name=item["name"],
            cost=_fraction(item["cost"]),
            observations=dict(item["observations"]),
        )
        for item in experiments_data
    )
    return ActiveDiscoveryProblem(
        hypotheses, properties, experiments, prior
    )


def build_certificate(
    problem: ActiveDiscoveryProblem, case_name: str
) -> dict[str, object]:
    basis = problem.exact_fixed_basis()
    cegis = problem.cegis_basis()
    obstruction = problem.obstruction()
    policy = problem.optimal_policy()
    basis_cost = (
        None
        if basis is None
        else sum(
            (experiment.cost for experiment in basis), Fraction(0)
        )
    )
    payload: dict[str, object] = {
        "schema": "logic-power-v10/active-discovery-certificate/1",
        "case": case_name,
        "problem": problem.to_data(),
        "analysis": {
            "conflict_pairs": [
                list(pair) for pair in problem.conflict_pairs()
            ],
            "fixed_basis": (
                None
                if basis is None
                else [experiment.name for experiment in basis]
            ),
            "fixed_basis_cost": (
                None
                if basis_cost is None
                else [basis_cost.numerator, basis_cost.denominator]
            ),
            "cegis_basis": (
                None
                if cegis is None
                else [experiment.name for experiment in cegis]
            ),
            "obstruction": (
                None if obstruction is None else list(obstruction)
            ),
            "policy": policy,
        },
    }
    return {"payload": payload, "sha256": digest_payload(payload)}


def verify_certificate(
    certificate: Mapping[str, Any],
) -> list[str]:
    errors: list[str] = []
    payload = certificate.get("payload")
    digest = certificate.get("sha256")
    if not isinstance(payload, Mapping) or not isinstance(digest, str):
        return ["certificate-shape"]
    if digest_payload(payload) != digest:
        errors.append("payload-hash")
        return errors
    try:
        problem = problem_from_data(payload["problem"])
        expected = build_certificate(problem, str(payload["case"]))
    except Exception as exc:  # fail closed on malformed evidence
        return [f"rebuild:{type(exc).__name__}"]
    expected_analysis = expected["payload"]["analysis"]
    actual_analysis = payload.get("analysis")
    if canonical_json(expected_analysis) != canonical_json(
        actual_analysis
    ):
        errors.append("semantic-replay")
    return errors
