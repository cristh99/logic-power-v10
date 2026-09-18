"""Deterministic-simulator Monte Carlo Tree Search for Problem Solver v1."""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from fractions import Fraction
from types import MappingProxyType
from typing import Callable, Mapping, Sequence


ActionsFn = Callable[[str], Sequence[str]]
StepFn = Callable[[str, str], tuple[str, Fraction, bool]]


@dataclass
class _Node:
    state: str
    depth: int
    terminal: bool
    visits: int = 0
    total_return: Fraction = Fraction()
    children: dict[str, tuple[Fraction, "_Node"]] = field(default_factory=dict)


@dataclass(frozen=True)
class MCTSResult:
    """Root decision and exact sampled-return statistics."""

    action: str | None
    root_visits: int
    action_visits: Mapping[str, int]
    action_total_returns: Mapping[str, Fraction]
    action_mean_returns: Mapping[str, Fraction]
    rollouts: int
    seed: int
    horizon: int


def _normalized_actions(actions: ActionsFn, state: str) -> tuple[str, ...]:
    raw = actions(state)
    if not isinstance(raw, (list, tuple)):
        raise TypeError("actions(state) must return a sequence")
    normalized = tuple(
        action.strip() if isinstance(action, str) else action for action in raw
    )
    if any(not isinstance(action, str) or not action for action in normalized):
        raise ValueError("actions must be non-empty strings")
    if len(normalized) != len(set(normalized)):
        raise ValueError("actions must not contain duplicates")
    return tuple(sorted(normalized))


def _step_checked(
    step: StepFn,
    state: str,
    action: str,
) -> tuple[str, Fraction, bool]:
    result = step(state, action)
    if not isinstance(result, tuple) or len(result) != 3:
        raise TypeError("step must return (next_state, reward, terminal)")
    next_state, reward, terminal = result
    if not isinstance(next_state, str) or not next_state.strip():
        raise ValueError("step next_state must be a non-empty string")
    if not isinstance(reward, Fraction):
        raise TypeError("step reward must be Fraction")
    if not isinstance(terminal, bool):
        raise TypeError("step terminal flag must be bool")
    return next_state.strip(), reward, terminal


def _rollout(
    *,
    state: str,
    depth: int,
    terminal: bool,
    horizon: int,
    actions: ActionsFn,
    step: StepFn,
    rng: random.Random,
) -> Fraction:
    total = Fraction()
    current_state = state
    current_depth = depth
    current_terminal = terminal
    while current_depth < horizon and not current_terminal:
        candidates = _normalized_actions(actions, current_state)
        if not candidates:
            break
        action = candidates[rng.randrange(len(candidates))]
        current_state, reward, current_terminal = _step_checked(
            step,
            current_state,
            action,
        )
        total += reward
        current_depth += 1
    return total


def plan_with_mcts(
    *,
    start_state: str,
    actions: ActionsFn,
    step: StepFn,
    horizon: int,
    rollouts: int,
    seed: int,
    exploration: float = math.sqrt(2.0),
) -> MCTSResult:
    """Plan in a deterministic finite simulator using seeded UCT.

    This slice intentionally excludes stochastic chance nodes. Every simulator
    call for a given state/action must be deterministic. Approximation is in
    finite search allocation, while all sampled returns are accumulated exactly
    as ``Fraction`` values.
    """

    if not isinstance(start_state, str) or not start_state.strip():
        raise ValueError("start_state must be a non-empty string")
    if isinstance(horizon, bool) or not isinstance(horizon, int) or horizon < 0:
        raise ValueError("horizon must be a non-negative integer")
    if isinstance(rollouts, bool) or not isinstance(rollouts, int) or rollouts <= 0:
        raise ValueError("rollouts must be a positive integer")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise TypeError("seed must be an integer")
    if not isinstance(exploration, (int, float)) or isinstance(exploration, bool):
        raise TypeError("exploration must be a real number")
    exploration = float(exploration)
    if not math.isfinite(exploration) or exploration < 0:
        raise ValueError("exploration must be finite and non-negative")

    root = _Node(start_state.strip(), 0, horizon == 0)
    rng = random.Random(seed)
    observed_transitions: dict[
        tuple[str, str], tuple[str, Fraction, bool]
    ] = {}

    def deterministic_step(
        state: str, action: str
    ) -> tuple[str, Fraction, bool]:
        result = _step_checked(step, state, action)
        key = (state, action)
        previous = observed_transitions.get(key)
        if previous is not None and previous != result:
            raise ValueError(
                "MCTS v1 requires a deterministic simulator; "
                f"{key} produced both {previous} and {result}"
            )
        observed_transitions[key] = result
        return result

    for _ in range(rollouts):
        node = root
        path_nodes = [root]
        path_edges: list[tuple[Fraction, _Node]] = []

        while node.depth < horizon and not node.terminal:
            candidates = _normalized_actions(actions, node.state)
            if not candidates:
                node.terminal = True
                break

            unexpanded = [
                action for action in candidates if action not in node.children
            ]
            if unexpanded:
                action = unexpanded[rng.randrange(len(unexpanded))]
                next_state, reward, terminal = deterministic_step(
                    node.state,
                    action,
                )
                child = _Node(
                    state=next_state,
                    depth=node.depth + 1,
                    terminal=terminal or node.depth + 1 >= horizon,
                )
                node.children[action] = (reward, child)
                path_edges.append((reward, child))
                path_nodes.append(child)
                node = child
                break

            log_parent = math.log(max(1, node.visits))

            def selection_key(action: str) -> tuple[float, str]:
                reward, child = node.children[action]
                if child.visits <= 0:
                    score = math.inf
                else:
                    exploitation = float(
                        reward + child.total_return / child.visits
                    )
                    exploration_bonus = exploration * math.sqrt(
                        log_parent / child.visits
                    )
                    score = exploitation + exploration_bonus
                return (-score, action)

            action = min(candidates, key=selection_key)
            reward, child = node.children[action]
            path_edges.append((reward, child))
            path_nodes.append(child)
            node = child

        continuation = _rollout(
            state=node.state,
            depth=node.depth,
            terminal=node.terminal,
            horizon=horizon,
            actions=actions,
            step=deterministic_step,
            rng=rng,
        )

        path_nodes[-1].visits += 1
        path_nodes[-1].total_return += continuation
        for index in range(len(path_edges) - 1, -1, -1):
            reward, _child = path_edges[index]
            continuation = reward + continuation
            parent = path_nodes[index]
            parent.visits += 1
            parent.total_return += continuation

    action_visits: dict[str, int] = {}
    action_total_returns: dict[str, Fraction] = {}
    action_mean_returns: dict[str, Fraction] = {}
    for action in sorted(root.children):
        reward, child = root.children[action]
        visits = child.visits
        total = reward * visits + child.total_return
        action_visits[action] = visits
        action_total_returns[action] = total
        action_mean_returns[action] = (
            total / visits if visits else Fraction()
        )

    selected_action: str | None = None
    if action_visits:
        selected_action = min(
            action_visits,
            key=lambda action: (
                -action_visits[action],
                -action_mean_returns[action],
                action,
            ),
        )

    return MCTSResult(
        action=selected_action,
        root_visits=root.visits,
        action_visits=MappingProxyType(action_visits),
        action_total_returns=MappingProxyType(action_total_returns),
        action_mean_returns=MappingProxyType(action_mean_returns),
        rollouts=rollouts,
        seed=seed,
        horizon=horizon,
    )
