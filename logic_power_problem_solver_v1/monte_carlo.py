"""Seeded bounded Monte Carlo estimates with a Hoeffding confidence radius."""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class MonteCarloEstimate:
    mean: float
    radius: float
    lower_bound: float
    upper_bound: float
    samples: int
    confidence: float
    seed: int


def estimate_bounded_mean(
    sampler: Callable[[random.Random], float],
    samples: int,
    *,
    lower: float,
    upper: float,
    confidence: float,
    seed: int,
) -> MonteCarloEstimate:
    if samples <= 0:
        raise ValueError("samples must be positive")
    if not 0.0 < confidence < 1.0:
        raise ValueError("confidence must lie strictly between zero and one")
    if not lower < upper:
        raise ValueError("lower must be strictly smaller than upper")

    rng = random.Random(seed)
    total = 0.0
    for _ in range(samples):
        value = float(sampler(rng))
        if not lower <= value <= upper:
            raise ValueError("sample lies outside declared bounds")
        total += value

    mean = total / samples
    delta = 1.0 - confidence
    radius = (upper - lower) * math.sqrt(math.log(2.0 / delta) / (2.0 * samples))
    return MonteCarloEstimate(
        mean=mean,
        radius=radius,
        lower_bound=max(lower, mean - radius),
        upper_bound=min(upper, mean + radius),
        samples=samples,
        confidence=confidence,
        seed=seed,
    )
