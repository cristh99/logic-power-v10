"""Dual lower bounds for the minimum fixed basis of an active-discovery problem.

The minimum fixed basis is the minimum-cost hitting set of all conflict pairs.
This module computes a *dual witness*: non-negative rational weights ``y_p`` on
conflict pairs such that every experiment ``e`` satisfies

    sum_{p separated by e} y_p <= cost(e).

For any separating basis ``B`` every conflict pair is hit by at least one
``e in B``, hence

    cost(B) = sum_{e in B} cost(e)
            >= sum_{e in B} sum_{p separated by e} y_p
            >= sum_p y_p,

so the dual value is a lower bound on the cost of *every* separating basis
(weak LP duality of the hitting-set relaxation). When the dual value equals
the declared basis cost, the basis is certified minimum without enumerating
2^|E| subsets.
"""
from __future__ import annotations

from fractions import Fraction

from logic_power_v10.active_discovery import (
    ActiveDiscoveryProblem,
    Experiment,
    Pair,
)


def separates(experiment: Experiment, pair: Pair) -> bool:
    """Whether ``experiment`` gives different observations to the pair."""
    left, right = pair
    return experiment.observations[left] != experiment.observations[right]


def forced_experiments(
    problem: ActiveDiscoveryProblem,
) -> list[tuple[str, Pair]] | None:
    """Experiments that must appear in every separating basis.

    A conflict pair with exactly one separating experiment forces that
    experiment into every basis (the executable counterpart of the Lean
    theorem ``missing_required_coordinate_cannot_separate``). Returns one
    ``(experiment_name, witness_pair)`` entry per forced experiment, sorted
    by experiment name, where the witness is the canonically smallest
    conflict pair only that experiment separates. Returns ``None`` when the
    problem has an obstruction.
    """
    if problem.obstruction() is not None:
        return None
    witness: dict[str, Pair] = {}
    for pair in problem.conflict_pairs():
        separators = [
            experiment
            for experiment in problem.experiments
            if separates(experiment, pair)
        ]
        if len(separators) == 1:
            name = separators[0].name
            if name not in witness or pair < witness[name]:
                witness[name] = pair
    return sorted(witness.items())


def dual_lower_bound(
    problem: ActiveDiscoveryProblem,
) -> tuple[dict[Pair, Fraction], Fraction] | None:
    """Deterministic primal-dual lower bound on every separating basis.

    Processes conflict pairs fewest-separators-first (canonical order as
    tie-break) and raises each pair's weight to the smallest residual
    capacity of its separators. The returned weights satisfy, for every
    experiment ``e``, ``sum_{p separated by e} y_p <= cost(e)``, so their
    total lower-bounds the cost of every separating basis by weak LP
    duality. Returns ``None`` when some conflict pair has no separator
    (the problem has an obstruction).
    """
    conflicts = problem.conflict_pairs()
    seps = {
        pair: [
            experiment
            for experiment in problem.experiments
            if separates(experiment, pair)
        ]
        for pair in conflicts
    }
    if any(not seps[pair] for pair in conflicts):
        return None
    order = sorted(conflicts, key=lambda pair: (len(seps[pair]), pair))
    capacity = {
        experiment.name: experiment.cost
        for experiment in problem.experiments
    }
    weights: dict[Pair, Fraction] = {}
    for pair in order:
        value = min(capacity[experiment.name] for experiment in seps[pair])
        if value > 0:
            weights[pair] = value
            for experiment in seps[pair]:
                capacity[experiment.name] -= value
    return weights, sum(weights.values(), Fraction(0))
