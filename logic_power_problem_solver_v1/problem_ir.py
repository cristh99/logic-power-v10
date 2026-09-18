"""Typed, canonical problem representation for Logic Power Problem Solver v1."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping


MAX_SAFE_INTEGER = 2**53 - 1


class ConditionKind(str, Enum):
    FACT = "FACT"
    GOAL = "GOAL"
    HARD_CONSTRAINT = "HARD_CONSTRAINT"
    SOFT_PREFERENCE = "SOFT_PREFERENCE"
    SAFETY_INVARIANT = "SAFETY_INVARIANT"
    BUDGET = "BUDGET"
    EVIDENCE_REQUIREMENT = "EVIDENCE_REQUIREMENT"


class TerminalStatus(str, Enum):
    SOLVED = "SOLVED"
    IMPOSSIBLE = "IMPOSSIBLE"
    BLOCKED = "BLOCKED"
    UNDERSPECIFIED = "UNDERSPECIFIED"
    BUDGET_EXHAUSTED = "BUDGET_EXHAUSTED"
    UNSAFE = "UNSAFE"


class Horizon(str, Enum):
    STATIC = "STATIC"
    FINITE = "FINITE"
    INFINITE_DISCOUNTED = "INFINITE_DISCOUNTED"
    RECEDING = "RECEDING"


class UncertaintyKind(str, Enum):
    NONE = "NONE"
    PROBABILISTIC = "PROBABILISTIC"
    INTERVAL = "INTERVAL"
    ADVERSARIAL = "ADVERSARIAL"
    UNKNOWN = "UNKNOWN"


class ModelStatus(str, Enum):
    KNOWN = "KNOWN"
    PARTIAL = "PARTIAL"
    SIMULATOR = "SIMULATOR"
    LEARNABLE = "LEARNABLE"
    UNKNOWN = "UNKNOWN"


def _freeze_json(value: Any) -> Any:
    """Deep-copy JSON-like metadata into an immutable, exact representation."""
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Mapping):
        frozen: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError("metadata keys must be strings")
            if key in frozen:
                raise ValueError(f"duplicate metadata key: {key}")
            frozen[key] = _freeze_json(item)
        return MappingProxyType(frozen)
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_json(item) for item in value)
    if isinstance(value, bool) or value is None or isinstance(value, str):
        return value
    if isinstance(value, int):
        if abs(value) > MAX_SAFE_INTEGER:
            raise ValueError(
                "integer metadata exceeds the cross-runtime safe range; "
                "encode it as a decimal string"
            )
        return value
    if isinstance(value, float):
        raise TypeError(
            "floating-point metadata is not canonical; "
            "use a rational pair or decimal string"
        )
    raise TypeError(f"unsupported canonical JSON value: {type(value).__name__}")


def _normalize_json(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Mapping):
        return {key: _normalize_json(value[key]) for key in sorted(value)}
    if isinstance(value, (list, tuple)):
        return [_normalize_json(item) for item in value]
    if isinstance(value, bool) or value is None or isinstance(value, (str, int)):
        return value
    raise TypeError(f"unsupported frozen JSON value: {type(value).__name__}")


@dataclass(frozen=True)
class Condition:
    name: str
    kind: ConditionKind
    expression: str
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("condition name must be a non-empty string")
        if not isinstance(self.kind, ConditionKind):
            raise TypeError("condition kind must be ConditionKind")
        if not isinstance(self.expression, str) or not self.expression.strip():
            raise ValueError("condition expression must be a non-empty string")
        if not isinstance(self.metadata, Mapping):
            raise TypeError("condition metadata must be a mapping")
        object.__setattr__(self, "name", self.name.strip())
        object.__setattr__(self, "expression", self.expression.strip())
        object.__setattr__(self, "metadata", _freeze_json(dict(self.metadata)))

    def canonical_data(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "kind": self.kind.value,
            "expression": self.expression,
            "metadata": _normalize_json(self.metadata),
        }


@dataclass(frozen=True)
class SearchBudget:
    rollouts: int = 0
    max_depth: int = 0
    time_ms: int = 0
    memory_mb: int = 0

    def __post_init__(self) -> None:
        values = (self.rollouts, self.max_depth, self.time_ms, self.memory_mb)
        if any(
            isinstance(value, bool)
            or not isinstance(value, int)
            or value < 0
            or value > MAX_SAFE_INTEGER
            for value in values
        ):
            raise ValueError(
                "search budgets must be non-negative cross-runtime safe integers"
            )

    def canonical_data(self) -> dict[str, int]:
        return {
            "rollouts": self.rollouts,
            "max_depth": self.max_depth,
            "time_ms": self.time_ms,
            "memory_mb": self.memory_mb,
        }


@dataclass(frozen=True)
class ProblemIR:
    """Versioned finite/open-world boundary for one problem instance.

    Set-like registry fields are copied into immutable tuples and canonicalized
    in fingerprints. Ordered domain dynamics belong inside a typed adapter, not
    in these registries.
    """

    problem_id: str
    states: tuple[str, ...]
    initial_belief: tuple[str, ...]
    goal: str
    conditions: tuple[Condition, ...]
    actions: tuple[str, ...]
    experiments: tuple[str, ...]
    agents: tuple[str, ...]
    horizon: Horizon
    uncertainty: UncertaintyKind
    model_status: ModelStatus
    objective: str
    capabilities: tuple[str, ...]
    verifiers: tuple[str, ...]
    search_budget: SearchBudget = field(default_factory=SearchBudget)
    solution_concept: str | None = None
    schema: str = "logic-power-problem-ir/1"

    def __post_init__(self) -> None:
        if self.schema != "logic-power-problem-ir/1":
            raise ValueError(f"unsupported Problem IR schema: {self.schema}")
        for field_name, enum_type in (
            ("horizon", Horizon),
            ("uncertainty", UncertaintyKind),
            ("model_status", ModelStatus),
        ):
            if not isinstance(getattr(self, field_name), enum_type):
                raise TypeError(f"{field_name} must be {enum_type.__name__}")
        if not isinstance(self.search_budget, SearchBudget):
            raise TypeError("search_budget must be SearchBudget")
        for field_name in ("problem_id", "goal", "objective"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must be a non-empty string")

        normalized_fields: dict[str, tuple[str, ...]] = {}
        for field_name in (
            "states",
            "initial_belief",
            "actions",
            "experiments",
            "agents",
            "capabilities",
            "verifiers",
        ):
            raw_values = getattr(self, field_name)
            if not isinstance(raw_values, (list, tuple)):
                raise TypeError(f"{field_name} must be a sequence")
            values = tuple(
                value.strip() if isinstance(value, str) else value
                for value in raw_values
            )
            if any(not isinstance(value, str) or not value for value in values):
                raise ValueError(f"{field_name} must contain non-empty strings")
            if len(values) != len(set(values)):
                raise ValueError(f"{field_name} must not contain duplicates")
            normalized_fields[field_name] = values

        if not normalized_fields["states"]:
            raise ValueError("at least one state is required")
        if not normalized_fields["initial_belief"]:
            raise ValueError("initial_belief must be non-empty")
        if not normalized_fields["agents"]:
            raise ValueError("at least one agent is required")

        state_set = set(normalized_fields["states"])
        if not set(normalized_fields["initial_belief"]).issubset(state_set):
            missing = sorted(
                set(normalized_fields["initial_belief"]) - state_set
            )
            raise ValueError(f"initial_belief contains unknown states: {missing}")

        if not isinstance(self.conditions, (list, tuple)):
            raise TypeError("conditions must be a sequence")
        conditions = tuple(self.conditions)
        if any(not isinstance(condition, Condition) for condition in conditions):
            raise TypeError("conditions must contain Condition values")
        condition_names = [condition.name for condition in conditions]
        if len(condition_names) != len(set(condition_names)):
            raise ValueError("condition names must be unique")

        if self.solution_concept is not None:
            if (
                not isinstance(self.solution_concept, str)
                or not self.solution_concept.strip()
            ):
                raise ValueError("solution_concept must be non-empty when provided")
            object.__setattr__(
                self,
                "solution_concept",
                self.solution_concept.strip(),
            )

        object.__setattr__(self, "problem_id", self.problem_id.strip())
        object.__setattr__(self, "goal", self.goal.strip())
        object.__setattr__(self, "objective", self.objective.strip())
        object.__setattr__(self, "conditions", conditions)
        for field_name, values in normalized_fields.items():
            object.__setattr__(self, field_name, values)

    def canonical_data(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "problem_id": self.problem_id,
            "states": sorted(self.states),
            "initial_belief": sorted(self.initial_belief),
            "goal": self.goal,
            "conditions": [
                condition.canonical_data()
                for condition in sorted(
                    self.conditions,
                    key=lambda item: (
                        item.name,
                        item.kind.value,
                        item.expression,
                    ),
                )
            ],
            "actions": sorted(self.actions),
            "experiments": sorted(self.experiments),
            "agents": sorted(self.agents),
            "horizon": self.horizon.value,
            "uncertainty": self.uncertainty.value,
            "model_status": self.model_status.value,
            "objective": self.objective,
            "capabilities": sorted(self.capabilities),
            "verifiers": sorted(self.verifiers),
            "search_budget": self.search_budget.canonical_data(),
            "solution_concept": self.solution_concept,
        }

    def canonical_json(self) -> str:
        return json.dumps(
            self.canonical_data(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )

    def fingerprint(self) -> str:
        return hashlib.sha256(
            self.canonical_json().encode("utf-8")
        ).hexdigest()
