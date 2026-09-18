"""Fixed-basis bound certificates for Logic Power v10.

Schema ``logic-power-v10/fixed-basis-bound-certificate/1`` carries, besides
the problem payload, an exact minimum fixed basis, the forced-experiment
witnesses and a feasible dual weighting of conflict pairs whose value is a
lower bound on the cost of every separating basis. The certificate proves
minimality of ``fixed_basis`` only when ``tight`` is true; otherwise it
proves a valid lower bound and defers minimality to the core certificate's
replay.
"""
from __future__ import annotations

from fractions import Fraction
from typing import Any, Mapping

from logic_power_v10.active_discovery import ActiveDiscoveryProblem
from logic_power_v10.certificate import (
    canonical_json,
    digest_payload,
    problem_from_data,
)

from .bounds import dual_lower_bound, forced_experiments, separates

SCHEMA = "logic-power-v10/fixed-basis-bound-certificate/1"


def _fraction_data(value: Fraction) -> list[int]:
    return [value.numerator, value.denominator]


def _pair_data(pair: tuple[str, str]) -> list[str]:
    return [pair[0], pair[1]]


def build_bound_certificate(
    problem: ActiveDiscoveryProblem,
    case_name: str,
    parent_certificate_sha256: str | None = None,
) -> dict[str, object]:
    """Build a deterministic bound certificate for ``problem``."""
    obstruction = problem.obstruction()
    if obstruction is not None:
        analysis: dict[str, object] = {
            "obstruction": _pair_data(obstruction),
            "fixed_basis": None,
            "fixed_basis_cost": None,
            "forced_experiments": None,
            "dual": None,
            "tight": None,
        }
    else:
        basis = problem.exact_fixed_basis()
        assert basis is not None
        basis_cost = sum(
            (experiment.cost for experiment in basis), Fraction(0)
        )
        forced = forced_experiments(problem)
        assert forced is not None
        dual = dual_lower_bound(problem)
        assert dual is not None
        weights, value = dual
        analysis = {
            "obstruction": None,
            "fixed_basis": [
                experiment.name for experiment in basis
            ],
            "fixed_basis_cost": _fraction_data(basis_cost),
            "forced_experiments": [
                {
                    "experiment": name,
                    "witness_pair": _pair_data(pair),
                }
                for name, pair in forced
            ],
            "dual": {
                "weights": [
                    [_pair_data(pair), _fraction_data(weight)]
                    for pair, weight in sorted(weights.items())
                ],
                "value": _fraction_data(value),
            },
            "tight": value == basis_cost,
        }
    payload: dict[str, object] = {
        "schema": SCHEMA,
        "case": case_name,
        "parent_certificate_sha256": parent_certificate_sha256,
        "problem": problem.to_data(),
        "analysis": analysis,
    }
    return {"payload": payload, "sha256": digest_payload(payload)}


def _fraction(value: object) -> Fraction:
    if not isinstance(value, list) or len(value) != 2:
        raise ValueError("fraction must be [numerator, denominator]")
    numerator, denominator = value
    if (
        not isinstance(numerator, int)
        or isinstance(numerator, bool)
        or not isinstance(denominator, int)
        or isinstance(denominator, bool)
        or denominator <= 0
    ):
        raise ValueError("invalid fraction")
    return Fraction(numerator, denominator)


def _is_pair(value: object) -> bool:
    return (
        isinstance(value, list)
        and len(value) == 2
        and all(isinstance(item, str) for item in value)
    )


def _declared_forced(value: object) -> list[dict[str, object]] | None:
    if not isinstance(value, list):
        return None
    for entry in value:
        if (
            not isinstance(entry, Mapping)
            or not isinstance(entry.get("experiment"), str)
            or not _is_pair(entry.get("witness_pair"))
        ):
            return None
    return value


def _parse_dual(
    value: object, conflict_set: set[tuple[str, str]]
) -> tuple[dict[tuple[str, str], Fraction], Fraction] | None:
    """Parse the declared dual object; ``None`` when malformed."""
    if not isinstance(value, Mapping):
        return None
    weights_data = value.get("weights")
    declared_value = value.get("value")
    if not isinstance(weights_data, list):
        return None
    weights: dict[tuple[str, str], Fraction] = {}
    previous: tuple[str, str] | None = None
    for entry in weights_data:
        if (
            not isinstance(entry, list)
            or len(entry) != 2
            or not _is_pair(entry[0])
        ):
            return None
        pair = (entry[0][0], entry[0][1])
        if pair[0] >= pair[1] or pair not in conflict_set:
            return None
        if previous is not None and pair <= previous:
            return None
        previous = pair
        try:
            weight = _fraction(entry[1])
        except ValueError:
            return None
        if weight <= 0:
            return None
        weights[pair] = weight
    try:
        parsed_value = _fraction(declared_value)
    except ValueError:
        return None
    return weights, parsed_value


def verify_bound_certificate(
    certificate: Mapping[str, Any],
) -> list[str]:
    """Fail-closed check of a fixed-basis bound certificate.

    Every check is polynomial in the payload; none enumerates subsets of
    the experiment set. ``semantic-replay`` additionally rebuilds the
    analysis through :func:`build_bound_certificate` as a determinism
    check (the Node verifier does not rebuild).
    """
    payload = (
        certificate.get("payload")
        if isinstance(certificate, Mapping)
        else None
    )
    digest = (
        certificate.get("sha256")
        if isinstance(certificate, Mapping)
        else None
    )
    if not isinstance(payload, Mapping) or not isinstance(digest, str):
        return ["certificate-shape"]
    if digest_payload(payload) != digest:
        return ["payload-hash"]

    errors: list[str] = []
    if payload.get("schema") != SCHEMA:
        errors.append("schema")

    try:
        problem = problem_from_data(payload["problem"])
    except Exception:
        return errors + ["problem-shape"]
    if not all(
        isinstance(hypothesis, str) for hypothesis in problem.hypotheses
    ):
        return errors + ["problem-shape"]
    try:
        conflicts = problem.conflict_pairs()
        actual_obstruction = problem.obstruction()
        expected_forced = forced_experiments(problem)
    except Exception:
        return errors + ["problem-shape"]

    analysis = payload.get("analysis")
    if not isinstance(analysis, Mapping):
        analysis = {}
    conflict_set = set(conflicts)
    experiment_costs = {
        experiment.name: experiment.cost
        for experiment in problem.experiments
    }

    declared_obstruction = analysis.get("obstruction")
    if canonical_json(declared_obstruction) != canonical_json(
        _pair_data(actual_obstruction)
        if actual_obstruction is not None
        else None
    ):
        errors.append("obstruction")

    if actual_obstruction is not None:
        if any(
            analysis.get(field) is not None
            for field in (
                "fixed_basis",
                "fixed_basis_cost",
                "forced_experiments",
                "dual",
                "tight",
            )
        ):
            errors.append("impossible-shape")
    else:
        declared_basis = analysis.get("fixed_basis")
        basis_names: list[str] = []
        if (
            not isinstance(declared_basis, list)
            or any(not isinstance(name, str) for name in declared_basis)
            or len(set(declared_basis)) != len(declared_basis)
            or any(
                name not in experiment_costs for name in declared_basis
            )
        ):
            errors.append("basis-cover")
        else:
            basis_names = list(declared_basis)
            basis_experiments = [
                experiment
                for experiment in problem.experiments
                if experiment.name in set(basis_names)
            ]
            if any(
                not any(
                    separates(experiment, pair)
                    for experiment in basis_experiments
                )
                for pair in conflicts
            ):
                errors.append("basis-cover")

        declared_cost: Fraction | None = None
        try:
            declared_cost = _fraction(
                analysis.get("fixed_basis_cost")
            )
        except ValueError:
            errors.append("basis-cost")
        else:
            actual_cost = sum(
                (experiment_costs[name] for name in basis_names),
                Fraction(0),
            )
            if declared_cost != actual_cost:
                errors.append("basis-cost")

        declared_forced = _declared_forced(
            analysis.get("forced_experiments")
        )
        expected_forced_data = (
            [
                {
                    "experiment": name,
                    "witness_pair": _pair_data(pair),
                }
                for name, pair in expected_forced
            ]
            if expected_forced is not None
            else None
        )
        if canonical_json(declared_forced) != canonical_json(
            expected_forced_data
        ):
            errors.append("forced-experiments")
        if declared_forced is not None and not {
            entry["experiment"] for entry in declared_forced
        } <= set(basis_names):
            errors.append("forced-subset")

        dual_data = _parse_dual(analysis.get("dual"), conflict_set)
        dual_weights: dict[tuple[str, str], Fraction] = {}
        dual_value: Fraction | None = None
        if dual_data is None:
            errors.append("dual-shape")
        else:
            dual_weights, dual_value = dual_data
            for experiment in problem.experiments:
                load = sum(
                    (
                        weight
                        for pair, weight in dual_weights.items()
                        if separates(experiment, pair)
                    ),
                    Fraction(0),
                )
                if load > experiment.cost:
                    errors.append("dual-feasible")
                    break
            total = sum(dual_weights.values(), Fraction(0))
            if dual_value != total:
                errors.append("dual-value")
            if declared_cost is not None and dual_value > declared_cost:
                errors.append("dual-bound")

        declared_tight = analysis.get("tight")
        expected_tight = (
            dual_value is not None
            and declared_cost is not None
            and dual_value == declared_cost
        )
        if not isinstance(declared_tight, bool) or (
            declared_tight != expected_tight
        ):
            errors.append("tight-flag")

    try:
        expected = build_bound_certificate(
            problem,
            str(payload.get("case")),
            payload.get("parent_certificate_sha256"),
        )
        expected_analysis = expected["payload"]["analysis"]
        if canonical_json(expected_analysis) != canonical_json(analysis):
            errors.append("semantic-replay")
    except Exception:
        errors.append("semantic-replay")

    return errors
