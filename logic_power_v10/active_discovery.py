from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
from functools import lru_cache
from itertools import combinations
from typing import Iterable, Mapping, Sequence

Pair = tuple[str, str]


class MonitorStatus(str, Enum):
    TRUE = "TRUE"
    FALSE = "FALSE"
    UNKNOWN = "UNKNOWN"
    INCONSISTENT = "INCONSISTENT"
    IMPOSSIBLE = "IMPOSSIBLE"


def _fraction_data(value: Fraction) -> list[int]:
    return [value.numerator, value.denominator]


def _canonical_pair(left: str, right: str) -> Pair:
    return (left, right) if left < right else (right, left)


@dataclass(frozen=True)
class Experiment:
    name: str
    cost: Fraction
    observations: Mapping[str, str]

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("experiment name must be non-empty")
        if self.cost <= 0:
            raise ValueError("experiment cost must be positive")


class ActiveDiscoveryProblem:
    """Finite deterministic active-discovery problem.

    A problem is exactly decidable when every pair of hypotheses with opposite
    property values is separated by at least one admissible experiment.
    """

    def __init__(
        self,
        hypotheses: Sequence[str],
        property_values: Mapping[str, bool],
        experiments: Sequence[Experiment],
        prior: Mapping[str, Fraction] | None = None,
    ) -> None:
        self.hypotheses = tuple(hypotheses)
        self.property_values = dict(property_values)
        self.experiments = tuple(sorted(experiments, key=lambda exp: exp.name))
        if prior is None:
            prior = {
                hypothesis: Fraction(1, len(self.hypotheses))
                for hypothesis in self.hypotheses
            }
        self.prior = dict(prior)
        self._validate()

    def _validate(self) -> None:
        if not self.hypotheses:
            raise ValueError("at least one hypothesis is required")
        if len(set(self.hypotheses)) != len(self.hypotheses):
            raise ValueError("hypothesis identifiers must be unique")
        expected = set(self.hypotheses)
        if set(self.property_values) != expected:
            raise ValueError("property values must cover exactly the hypotheses")
        names = [experiment.name for experiment in self.experiments]
        if len(set(names)) != len(names):
            raise ValueError("experiment names must be unique")
        for experiment in self.experiments:
            if set(experiment.observations) != expected:
                raise ValueError(
                    f"experiment {experiment.name} must observe every hypothesis"
                )
        if set(self.prior) != expected:
            raise ValueError("prior must cover exactly the hypotheses")
        if any(weight <= 0 for weight in self.prior.values()):
            raise ValueError("prior weights must be positive")
        total = sum(self.prior.values(), Fraction(0))
        if total <= 0:
            raise ValueError("prior must have positive total mass")
        self.prior = {
            hypothesis: weight / total for hypothesis, weight in self.prior.items()
        }

    def monitor(self, belief: Iterable[str]) -> MonitorStatus:
        normalized = frozenset(belief)
        if not normalized:
            return MonitorStatus.INCONSISTENT
        if not normalized <= set(self.hypotheses):
            raise ValueError("belief contains an unknown hypothesis")
        values = {self.property_values[hypothesis] for hypothesis in normalized}
        if values == {True}:
            return MonitorStatus.TRUE
        if values == {False}:
            return MonitorStatus.FALSE
        return MonitorStatus.UNKNOWN

    def conflict_pairs(
        self, belief: Iterable[str] | None = None
    ) -> tuple[Pair, ...]:
        candidates = tuple(
            sorted(self.hypotheses if belief is None else set(belief))
        )
        return tuple(
            _canonical_pair(left, right)
            for left, right in combinations(candidates, 2)
            if self.property_values[left] != self.property_values[right]
        )

    @staticmethod
    def _separates(experiment: Experiment, pair: Pair) -> bool:
        left, right = pair
        return experiment.observations[left] != experiment.observations[right]

    def obstruction(self, belief: Iterable[str] | None = None) -> Pair | None:
        for pair in self.conflict_pairs(belief):
            if not any(
                self._separates(experiment, pair)
                for experiment in self.experiments
            ):
                return pair
        return None

    def exact_fixed_basis(self) -> tuple[Experiment, ...] | None:
        conflicts = set(self.conflict_pairs())
        if not conflicts:
            return ()
        if self.obstruction() is not None:
            return None
        best: tuple[
            Fraction, int, tuple[str, ...], tuple[Experiment, ...]
        ] | None = None
        for size in range(1, len(self.experiments) + 1):
            for selected in combinations(self.experiments, size):
                covered = {
                    pair
                    for pair in conflicts
                    if any(
                        self._separates(experiment, pair)
                        for experiment in selected
                    )
                }
                if covered != conflicts:
                    continue
                names = tuple(experiment.name for experiment in selected)
                candidate = (
                    sum(
                        (experiment.cost for experiment in selected),
                        Fraction(0),
                    ),
                    size,
                    names,
                    selected,
                )
                if best is None or candidate[:3] < best[:3]:
                    best = candidate
        return None if best is None else best[3]

    def cegis_basis(self) -> tuple[Experiment, ...] | None:
        """Construct a separating basis by conflict-guided exact completion."""
        conflicts = set(self.conflict_pairs())
        if not conflicts:
            return ()
        if self.obstruction() is not None:
            return None
        selected: list[Experiment] = []
        uncovered = set(conflicts)
        while uncovered:
            witness = min(uncovered)
            candidates = [
                experiment
                for experiment in self.experiments
                if experiment not in selected
                and self._separates(experiment, witness)
            ]
            if not candidates:
                return None
            chosen = min(
                candidates,
                key=lambda experiment: (
                    -sum(
                        self._separates(experiment, pair)
                        for pair in uncovered
                    ),
                    experiment.cost,
                    experiment.name,
                ),
            )
            selected.append(chosen)
            uncovered = {
                pair
                for pair in uncovered
                if not any(
                    self._separates(experiment, pair)
                    for experiment in selected
                )
            }
        return tuple(selected)

    def optimal_policy(self) -> dict[str, object]:
        all_hypotheses = frozenset(self.hypotheses)

        def mass(belief: frozenset[str]) -> Fraction:
            return sum(
                (self.prior[hypothesis] for hypothesis in belief),
                Fraction(0),
            )

        @lru_cache(maxsize=None)
        def solve(
            belief: frozenset[str],
        ) -> tuple[bool, Fraction, Fraction, dict[str, object]]:
            status = self.monitor(belief)
            belief_list = sorted(belief)
            if status in (MonitorStatus.TRUE, MonitorStatus.FALSE):
                node = {
                    "belief": belief_list,
                    "status": status.value,
                    "worst_cost": [0, 1],
                    "expected_cost": [0, 1],
                }
                return True, Fraction(0), Fraction(0), node

            candidates: list[
                tuple[Fraction, Fraction, str, dict[str, object]]
            ] = []
            belief_mass = mass(belief)
            for experiment in self.experiments:
                groups: dict[str, frozenset[str]] = {}
                for hypothesis in belief:
                    observation = experiment.observations[hypothesis]
                    groups.setdefault(observation, frozenset())
                    groups[observation] = groups[observation] | {hypothesis}
                if len(groups) <= 1:
                    continue
                children: dict[str, dict[str, object]] = {}
                child_costs: list[Fraction] = []
                expected = experiment.cost
                exact = True
                for observation in sorted(groups):
                    child_belief = groups[observation]
                    (
                        child_exact,
                        child_worst,
                        child_expected,
                        child_node,
                    ) = solve(child_belief)
                    if not child_exact:
                        exact = False
                        break
                    children[observation] = child_node
                    child_costs.append(child_worst)
                    expected += (
                        mass(child_belief) / belief_mass * child_expected
                    )
                if not exact:
                    continue
                worst = experiment.cost + max(
                    child_costs, default=Fraction(0)
                )
                node = {
                    "belief": belief_list,
                    "status": MonitorStatus.UNKNOWN.value,
                    "experiment": experiment.name,
                    "experiment_cost": _fraction_data(experiment.cost),
                    "worst_cost": _fraction_data(worst),
                    "expected_cost": _fraction_data(expected),
                    "children": children,
                }
                candidates.append(
                    (worst, expected, experiment.name, node)
                )

            if candidates:
                worst, expected, _, node = min(
                    candidates, key=lambda candidate: candidate[:3]
                )
                return True, worst, expected, node

            obstruction = self.obstruction(belief)
            if obstruction is None:
                raise AssertionError(
                    "finite separation theorem violated: no policy and no obstruction"
                )
            node = {
                "belief": belief_list,
                "status": MonitorStatus.IMPOSSIBLE.value,
                "obstruction": list(obstruction),
                "worst_cost": [0, 1],
                "expected_cost": [0, 1],
            }
            return False, Fraction(0), Fraction(0), node

        exact, worst, expected, tree = solve(all_hypotheses)
        return {
            "exact": exact,
            "worst_cost": _fraction_data(worst),
            "expected_cost": _fraction_data(expected),
            "tree": tree,
        }

    def to_data(self) -> dict[str, object]:
        return {
            "hypotheses": [
                {
                    "id": hypothesis,
                    "property": self.property_values[hypothesis],
                    "prior": _fraction_data(self.prior[hypothesis]),
                }
                for hypothesis in sorted(self.hypotheses)
            ],
            "experiments": [
                {
                    "name": experiment.name,
                    "cost": _fraction_data(experiment.cost),
                    "observations": {
                        hypothesis: experiment.observations[hypothesis]
                        for hypothesis in sorted(self.hypotheses)
                    },
                }
                for experiment in self.experiments
            ],
        }


def make_or_problem(bits: int = 8) -> ActiveDiscoveryProblem:
    if bits <= 0:
        raise ValueError("bits must be positive")
    hypotheses = tuple(
        format(value, f"0{bits}b") for value in range(2**bits)
    )
    property_values = {
        hypothesis: "1" in hypothesis for hypothesis in hypotheses
    }
    experiments = tuple(
        Experiment(
            name=f"bit_{index}",
            cost=Fraction(1),
            observations={
                hypothesis: hypothesis[index] for hypothesis in hypotheses
            },
        )
        for index in range(bits)
    )
    return ActiveDiscoveryProblem(
        hypotheses, property_values, experiments
    )


def make_impossible_demo() -> ActiveDiscoveryProblem:
    hypotheses = ("false_world", "true_world")
    return ActiveDiscoveryProblem(
        hypotheses,
        {"false_world": False, "true_world": True},
        (
            Experiment(
                name="flat_sensor",
                cost=Fraction(1),
                observations={
                    hypothesis: "same" for hypothesis in hypotheses
                },
            ),
        ),
    )
