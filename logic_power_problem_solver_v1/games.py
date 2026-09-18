"""Exact small-game primitives for the strategic-decision layer."""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Sequence


@dataclass(frozen=True)
class ZeroSum2x2Result:
    kind: str
    row_strategy: tuple[Fraction, Fraction]
    column_strategy: tuple[Fraction, Fraction]
    value: Fraction


def _validate_matrix(
    matrix: Sequence[Sequence[Fraction]],
) -> tuple[tuple[Fraction, Fraction], tuple[Fraction, Fraction]]:
    if len(matrix) != 2 or any(len(row) != 2 for row in matrix):
        raise ValueError("expected a 2x2 payoff matrix")
    normalized = tuple(tuple(value for value in row) for row in matrix)
    if any(not isinstance(value, Fraction) for row in normalized for value in row):
        raise TypeError("payoffs must be fractions")
    return normalized  # type: ignore[return-value]


def solve_zero_sum_2x2(
    matrix: Sequence[Sequence[Fraction]],
) -> ZeroSum2x2Result:
    """Solve a 2x2 zero-sum game for the maximizing row player.

    Pure saddle points are preferred. Otherwise the unique interior mixed
    equilibrium is computed exactly with rational arithmetic.
    """
    payoffs = _validate_matrix(matrix)

    saddles: list[tuple[int, int, Fraction]] = []
    for row in range(2):
        row_min = min(payoffs[row])
        for column in range(2):
            value = payoffs[row][column]
            column_max = max(payoffs[0][column], payoffs[1][column])
            if value == row_min == column_max:
                saddles.append((row, column, value))
    if saddles:
        row, column, value = min(saddles)
        row_strategy = (Fraction(1), Fraction(0)) if row == 0 else (Fraction(0), Fraction(1))
        column_strategy = (
            (Fraction(1), Fraction(0))
            if column == 0
            else (Fraction(0), Fraction(1))
        )
        return ZeroSum2x2Result("PURE", row_strategy, column_strategy, value)

    a, b = payoffs[0]
    c, d = payoffs[1]
    denominator = a - b - c + d
    if denominator == 0:
        raise ValueError("degenerate 2x2 game has no unique interior equilibrium")

    row_first = (d - c) / denominator
    column_first = (d - b) / denominator
    if not (0 <= row_first <= 1 and 0 <= column_first <= 1):
        raise ValueError("equilibrium lies on a boundary not represented by a pure saddle")
    value = (a * d - b * c) / denominator
    return ZeroSum2x2Result(
        "MIXED",
        (row_first, 1 - row_first),
        (column_first, 1 - column_first),
        value,
    )
