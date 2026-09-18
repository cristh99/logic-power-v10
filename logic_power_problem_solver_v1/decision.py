"""Exact finite decision-theory primitives."""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Mapping


@dataclass(frozen=True)
class DecisionResult:
    action: str
    score: Fraction
    scores: Mapping[str, Fraction]
    criterion: str


def _validate_utilities(
    utilities: Mapping[str, Mapping[str, Fraction]],
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    if not utilities:
        raise ValueError("at least one action is required")
    actions = tuple(sorted(utilities))
    first_states = tuple(sorted(utilities[actions[0]]))
    if not first_states:
        raise ValueError("at least one state is required")
    expected = set(first_states)
    for action in actions:
        if set(utilities[action]) != expected:
            raise ValueError("every action must define utility for the same states")
        for value in utilities[action].values():
            if not isinstance(value, Fraction):
                raise TypeError("utilities must be fractions")
    return actions, first_states


def _validate_prior(prior: Mapping[str, Fraction], states: tuple[str, ...]) -> None:
    if set(prior) != set(states):
        raise ValueError("prior states must match utility states")
    if any(not isinstance(value, Fraction) or value < 0 for value in prior.values()):
        raise ValueError("prior probabilities must be non-negative fractions")
    if sum(prior.values(), Fraction()) != 1:
        raise ValueError("prior probabilities must sum to one")


def expected_utility_decision(
    prior: Mapping[str, Fraction],
    utilities: Mapping[str, Mapping[str, Fraction]],
) -> DecisionResult:
    actions, states = _validate_utilities(utilities)
    _validate_prior(prior, states)
    scores = {
        action: sum(
            (prior[state] * utilities[action][state] for state in states),
            Fraction(),
        )
        for action in actions
    }
    action = min(actions, key=lambda item: (-scores[item], item))
    return DecisionResult(action, scores[action], scores, "expected_utility")


def minimax_regret_decision(
    utilities: Mapping[str, Mapping[str, Fraction]],
) -> DecisionResult:
    actions, states = _validate_utilities(utilities)
    best_by_state = {
        state: max(utilities[action][state] for action in actions)
        for state in states
    }
    scores = {
        action: max(
            best_by_state[state] - utilities[action][state] for state in states
        )
        for action in actions
    }
    action = min(actions, key=lambda item: (scores[item], item))
    return DecisionResult(action, scores[action], scores, "minimax_regret")


def value_of_perfect_information(
    prior: Mapping[str, Fraction],
    utilities: Mapping[str, Mapping[str, Fraction]],
) -> Fraction:
    actions, states = _validate_utilities(utilities)
    _validate_prior(prior, states)
    current = expected_utility_decision(prior, utilities).score
    perfect = sum(
        (
            prior[state]
            * max(utilities[action][state] for action in actions)
            for state in states
        ),
        Fraction(),
    )
    return perfect - current
