"""Exhaustive small-case sweep of the finite separation theorem.

Enumerates every active-discovery problem with ``n`` hypotheses
``h0..h{n-1}`` for ``n in {2, 3}``, every property assignment in
``{False, True}^n`` and every non-empty subset of at most 3 of the
``2**n`` binary unit-cost experiments (observations in ``{"0", "1"}``),
and checks the theorem's invariants plus the dual bound on each one.
"""
from __future__ import annotations

import unittest
from fractions import Fraction
from itertools import combinations, product

from logic_power_v10.active_discovery import (
    ActiveDiscoveryProblem,
    Experiment,
)

from logic_power_fixed_basis_bound_v1.bounds import (
    dual_lower_bound,
    forced_experiments,
    separates,
)


def _experiment(bits: int, index: int) -> Experiment:
    pattern = format(index, f"0{bits}b")
    return Experiment(
        name=f"e{pattern}",
        cost=Fraction(1),
        observations={
            f"h{position}": symbol
            for position, symbol in enumerate(pattern)
        },
    )


def _all_problems(bits: int) -> list[ActiveDiscoveryProblem]:
    hypotheses = tuple(f"h{index}" for index in range(bits))
    experiments = tuple(
        _experiment(bits, index) for index in range(2**bits)
    )
    problems = []
    for property_bits in product((False, True), repeat=bits):
        property_values = dict(zip(hypotheses, property_bits))
        for size in (1, 2, 3):
            for subset in combinations(experiments, size):
                problems.append(
                    ActiveDiscoveryProblem(
                        hypotheses, property_values, subset
                    )
                )
    return problems


def _covers(problem: ActiveDiscoveryProblem, basis: tuple) -> bool:
    return all(
        any(separates(experiment, pair) for experiment in basis)
        for pair in problem.conflict_pairs()
    )


class SmallCaseSweepTests(unittest.TestCase):
    def test_exhaustive_sweep_n2_n3(self) -> None:
        problems = _all_problems(2) + _all_problems(3)
        exact_count = 0
        tight_count = 0
        for problem in problems:
            obstruction = problem.obstruction()
            basis = problem.exact_fixed_basis()
            cegis = problem.cegis_basis()
            policy = problem.optimal_policy()
            self.assertEqual(basis is None, obstruction is not None)
            self.assertEqual(cegis is None, obstruction is not None)
            self.assertEqual(
                policy["exact"], obstruction is None
            )
            if obstruction is None:
                exact_count += 1
                self.assertTrue(_covers(problem, basis))
                self.assertTrue(_covers(problem, cegis))
                dual = dual_lower_bound(problem)
                self.assertIsNotNone(dual)
                weights, value = dual
                for experiment in problem.experiments:
                    load = sum(
                        (
                            weight
                            for pair, weight in weights.items()
                            if separates(experiment, pair)
                        ),
                        Fraction(0),
                    )
                    self.assertLessEqual(load, experiment.cost)
                basis_cost = sum(
                    (experiment.cost for experiment in basis),
                    Fraction(0),
                )
                self.assertLessEqual(value, basis_cost)
                forced = forced_experiments(problem)
                self.assertIsNotNone(forced)
                basis_names = {
                    experiment.name for experiment in basis
                }
                for name, _pair in forced:
                    self.assertIn(name, basis_names)
                if value == basis_cost:
                    tight_count += 1
        self.assertEqual(len(problems), 792)
        self.assertEqual(exact_count, 636)
        print(
            f"sweep: {len(problems)} problems, "
            f"{exact_count} exact, {tight_count} tight"
        )


if __name__ == "__main__":
    unittest.main()
