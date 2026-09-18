"""Exact finite-horizon planning primitives for Problem Solver v1."""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from types import MappingProxyType
from typing import Mapping, Sequence


@dataclass(frozen=True)
class MDPTransition:
    """One exact transition outcome for a state/action pair."""

    next_state: str
    probability: Fraction
    reward: Fraction

    def __post_init__(self) -> None:
        if not isinstance(self.next_state, str) or not self.next_state.strip():
            raise ValueError("next_state must be a non-empty string")
        if not isinstance(self.probability, Fraction):
            raise TypeError("transition probability must be Fraction")
        if not isinstance(self.reward, Fraction):
            raise TypeError("transition reward must be Fraction")
        if not 0 <= self.probability <= 1:
            raise ValueError("transition probability must lie in [0, 1]")
        object.__setattr__(self, "next_state", self.next_state.strip())


@dataclass(frozen=True)
class FiniteMDPPlan:
    """Exact policy/value certificate for one finite-horizon MDP instance."""

    start_state: str
    start_action: str | None
    start_value: Fraction
    horizon: int
    discount: Fraction
    policy: Mapping[str, str]
    values: Mapping[str, Fraction]


def _normalize_string_sequence(
    values: Sequence[str],
    *,
    name: str,
    allow_empty: bool,
) -> tuple[str, ...]:
    if not isinstance(values, (list, tuple)):
        raise TypeError(f"{name} must be a sequence")
    normalized = tuple(
        value.strip() if isinstance(value, str) else value for value in values
    )
    if not allow_empty and not normalized:
        raise ValueError(f"{name} must be non-empty")
    if any(not isinstance(value, str) or not value for value in normalized):
        raise ValueError(f"{name} must contain non-empty strings")
    if len(normalized) != len(set(normalized)):
        raise ValueError(f"{name} must not contain duplicates")
    return normalized


def solve_finite_horizon_mdp(
    *,
    states: Sequence[str],
    actions_by_state: Mapping[str, Sequence[str]],
    transitions: Mapping[tuple[str, str], Sequence[MDPTransition]],
    terminal_states: Sequence[str],
    start_state: str,
    horizon: int,
    discount: Fraction = Fraction(1),
) -> FiniteMDPPlan:
    """Solve a finite MDP exactly by backward dynamic programming.

    Values and probabilities use ``Fraction`` throughout. The policy is indexed
    by ``"time:state"`` so non-stationary finite-horizon decisions remain
    explicit. Ties are broken lexicographically for deterministic replay.
    """

    state_tuple = _normalize_string_sequence(
        states,
        name="states",
        allow_empty=False,
    )
    state_set = set(state_tuple)
    terminal_tuple = _normalize_string_sequence(
        terminal_states,
        name="terminal_states",
        allow_empty=True,
    )
    terminal_set = set(terminal_tuple)
    if not terminal_set.issubset(state_set):
        raise ValueError("terminal_states must be a subset of states")
    if not isinstance(start_state, str) or start_state.strip() not in state_set:
        raise ValueError("start_state must name a declared state")
    start_state = start_state.strip()
    if isinstance(horizon, bool) or not isinstance(horizon, int) or horizon < 0:
        raise ValueError("horizon must be a non-negative integer")
    if not isinstance(discount, Fraction):
        raise TypeError("discount must be Fraction")
    if not 0 <= discount <= 1:
        raise ValueError("discount must lie in [0, 1]")
    if set(actions_by_state) != state_set:
        missing = sorted(state_set - set(actions_by_state))
        extra = sorted(set(actions_by_state) - state_set)
        raise ValueError(
            f"actions_by_state must cover exactly the states; "
            f"missing={missing}, extra={extra}"
        )

    normalized_actions: dict[str, tuple[str, ...]] = {}
    for state in state_tuple:
        actions = _normalize_string_sequence(
            actions_by_state[state],
            name=f"actions_by_state[{state}]",
            allow_empty=state in terminal_set,
        )
        if state in terminal_set and actions:
            raise ValueError("terminal states must not declare actions")
        if state not in terminal_set and not actions:
            raise ValueError("non-terminal states must declare at least one action")
        normalized_actions[state] = tuple(sorted(actions))

    expected_keys = {
        (state, action)
        for state in state_tuple
        if state not in terminal_set
        for action in normalized_actions[state]
    }
    if set(transitions) != expected_keys:
        missing = sorted(expected_keys - set(transitions))
        extra = sorted(set(transitions) - expected_keys)
        raise ValueError(
            f"transitions must cover exactly every non-terminal action; "
            f"missing={missing}, extra={extra}"
        )

    normalized_transitions: dict[
        tuple[str, str], tuple[MDPTransition, ...]
    ] = {}
    for key in sorted(expected_keys):
        outcomes = transitions[key]
        if not isinstance(outcomes, (list, tuple)) or not outcomes:
            raise ValueError(f"transition outcomes must be non-empty for {key}")
        normalized = tuple(outcomes)
        if any(not isinstance(item, MDPTransition) for item in normalized):
            raise TypeError(f"transition outcomes must be MDPTransition for {key}")
        if any(item.next_state not in state_set for item in normalized):
            raise ValueError(f"transition references an unknown state for {key}")
        probability_mass = sum(
            (item.probability for item in normalized),
            Fraction(),
        )
        if probability_mass != 1:
            raise ValueError(
                f"transition probability mass must equal one for {key}; "
                f"got {probability_mass}"
            )
        normalized_transitions[key] = normalized

    values_by_time: list[dict[str, Fraction]] = [
        {} for _ in range(horizon + 1)
    ]
    values_by_time[horizon] = {state: Fraction() for state in state_tuple}
    policy: dict[str, str] = {}

    for time in range(horizon - 1, -1, -1):
        next_values = values_by_time[time + 1]
        current_values: dict[str, Fraction] = {}
        for state in sorted(state_tuple):
            if state in terminal_set:
                current_values[state] = Fraction()
                continue
            action_values: dict[str, Fraction] = {}
            for action in normalized_actions[state]:
                action_values[action] = sum(
                    (
                        outcome.probability
                        * (
                            outcome.reward
                            + discount * next_values[outcome.next_state]
                        )
                        for outcome in normalized_transitions[(state, action)]
                    ),
                    Fraction(),
                )
            selected_action = min(
                action_values,
                key=lambda action: (-action_values[action], action),
            )
            current_values[state] = action_values[selected_action]
            policy[f"{time}:{state}"] = selected_action
        values_by_time[time] = current_values

    flat_values = {
        f"{time}:{state}": values_by_time[time][state]
        for time in range(horizon + 1)
        for state in sorted(state_tuple)
    }
    start_action = (
        None
        if horizon == 0 or start_state in terminal_set
        else policy[f"0:{start_state}"]
    )
    return FiniteMDPPlan(
        start_state=start_state,
        start_action=start_action,
        start_value=values_by_time[0][start_state],
        horizon=horizon,
        discount=discount,
        policy=MappingProxyType(dict(sorted(policy.items()))),
        values=MappingProxyType(dict(sorted(flat_values.items()))),
    )
