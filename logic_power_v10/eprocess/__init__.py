from __future__ import annotations

from fractions import Fraction
from typing import Callable, Mapping, Sequence

BernoulliModel = Mapping[str, tuple[Fraction, Fraction]]
Policy = Callable[[tuple[int, ...], Fraction], str]


def likelihood_factor(
    sensor: str,
    outcome: int,
    null: BernoulliModel,
    alt: BernoulliModel,
) -> Fraction:
    """Return the one-step likelihood ratio for a predictable sensor choice."""
    if outcome not in (0, 1):
        raise ValueError("Bernoulli outcomes must be 0 or 1")
    if sensor not in null or sensor not in alt:
        raise KeyError(f"unknown sensor: {sensor}")
    p0 = null[sensor][outcome]
    p1 = alt[sensor][outcome]
    if p0 == 0:
        raise ZeroDivisionError("null assigns zero probability to an observed outcome")
    return p1 / p0


def _validate_models(
    sensors: Sequence[str],
    null: BernoulliModel,
    alt: BernoulliModel,
) -> tuple[str, ...]:
    normalized = tuple(sensors)
    if not normalized:
        raise ValueError("at least one sensor is required")
    if len(set(normalized)) != len(normalized):
        raise ValueError("sensor names must be unique")
    for sensor in normalized:
        if sensor not in null or sensor not in alt:
            raise KeyError(f"missing model for sensor: {sensor}")
        for name, model in (("null", null), ("alternative", alt)):
            probs = model[sensor]
            if len(probs) != 2 or any(p < 0 for p in probs):
                raise ValueError(f"invalid {name} Bernoulli law for {sensor}")
            if sum(probs, Fraction(0)) != 1:
                raise ValueError(f"{name} Bernoulli law for {sensor} must sum to one")
    return normalized


def enumerate_adaptive_eprocess(
    horizon: int,
    sensors: Sequence[str],
    null: BernoulliModel,
    alt: BernoulliModel,
    policy: Policy,
    stop_threshold: Fraction | None = None,
) -> dict[str, object]:
    """Enumerate the exact stopped experiment tree.

    The policy is predictable: it receives only the already observed history and
    the current e-value. A terminal prefix is counted once. This is essential:
    enumerating all unused suffixes after optional stopping would duplicate the
    same stopped event and corrupt the expectation.
    """
    if horizon < 0:
        raise ValueError("horizon must be nonnegative")
    sensor_names = _validate_models(sensors, null, alt)
    if stop_threshold is not None and stop_threshold <= 0:
        raise ValueError("stop_threshold must be positive")

    expectation = Fraction(0)
    stopped_expectation = Fraction(0)
    stopped_mass = Fraction(0)
    terminal_mass = Fraction(0)
    paths: list[dict[str, object]] = []

    def walk(
        history: tuple[int, ...],
        used: tuple[str, ...],
        probability: Fraction,
        e_value: Fraction,
    ) -> None:
        nonlocal expectation, stopped_expectation, stopped_mass, terminal_mass

        threshold_reached = (
            stop_threshold is not None
            and len(history) > 0
            and e_value >= stop_threshold
        )
        horizon_reached = len(history) == horizon
        if threshold_reached or horizon_reached:
            weighted_e = probability * e_value
            expectation += weighted_e
            stopped_expectation += weighted_e
            terminal_mass += probability
            if threshold_reached:
                stopped_mass += probability
            paths.append(
                {
                    "outcomes": list(history),
                    "sensors": list(used),
                    "probability": [probability.numerator, probability.denominator],
                    "e_value": [e_value.numerator, e_value.denominator],
                    "stopped": threshold_reached,
                    "terminal_reason": "threshold" if threshold_reached else "horizon",
                }
            )
            return

        sensor = policy(history, e_value)
        if sensor not in sensor_names:
            raise ValueError(f"policy selected unknown sensor {sensor}")
        for outcome in (0, 1):
            p0 = null[sensor][outcome]
            if p0 == 0:
                continue
            walk(
                history + (outcome,),
                used + (sensor,),
                probability * p0,
                e_value * likelihood_factor(sensor, outcome, null, alt),
            )

    walk((), (), Fraction(1), Fraction(1))
    if terminal_mass != 1:
        raise AssertionError(f"terminal prefixes do not partition the null law: {terminal_mass}")

    return {
        "horizon": horizon,
        "expectation": [expectation.numerator, expectation.denominator],
        "stopped_expectation": [
            stopped_expectation.numerator,
            stopped_expectation.denominator,
        ],
        "stopped_mass": [stopped_mass.numerator, stopped_mass.denominator],
        "terminal_mass": [terminal_mass.numerator, terminal_mass.denominator],
        "terminal_prefixes": len(paths),
        "paths": paths,
    }


def demo_models() -> tuple[tuple[str, ...], BernoulliModel, BernoulliModel, Policy]:
    sensors = ("A", "B")
    null: BernoulliModel = {
        "A": (Fraction(3, 4), Fraction(1, 4)),
        "B": (Fraction(1, 2), Fraction(1, 2)),
    }
    alt: BernoulliModel = {
        "A": (Fraction(1, 4), Fraction(3, 4)),
        "B": (Fraction(3, 4), Fraction(1, 4)),
    }

    def policy(history: tuple[int, ...], e_value: Fraction) -> str:
        del history
        return "A" if e_value <= 1 else "B"

    return sensors, null, alt, policy
