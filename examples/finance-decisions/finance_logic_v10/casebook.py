from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from itertools import product
from typing import Iterator, Mapping

from logic_power_v10.active_discovery import ActiveDiscoveryProblem, Experiment


Axis = tuple[str, tuple[str, str]]
ExperimentSpec = tuple[str, Fraction, str]


@dataclass(frozen=True)
class BinaryFinanceCase:
    """Finite exact financial decision contract over binary risk axes."""

    name: str
    axes: tuple[Axis, ...]
    adverse_values: Mapping[str, str]
    charges: Mapping[str, int]
    threshold: int
    experiments: tuple[ExperimentSpec, ...]
    positive_label: str
    negative_label: str

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("case name must be non-empty")
        axis_names = tuple(axis for axis, _ in self.axes)
        if len(set(axis_names)) != len(axis_names):
            raise ValueError("axis names must be unique")
        if set(self.adverse_values) != set(axis_names):
            raise ValueError("adverse values must cover every axis")
        if set(self.charges) != set(axis_names):
            raise ValueError("charges must cover every axis")
        if any(self.charges[axis] <= 0 for axis in axis_names):
            raise ValueError("charges must be positive")
        if self.threshold < 0:
            raise ValueError("threshold must be non-negative")
        for axis, options in self.axes:
            if len(options) != 2 or len(set(options)) != 2:
                raise ValueError(f"axis {axis} must have two unique values")
            if self.adverse_values[axis] not in options:
                raise ValueError(f"invalid adverse value for {axis}")
        experiment_names = tuple(name for name, _, _ in self.experiments)
        if len(set(experiment_names)) != len(experiment_names):
            raise ValueError("experiment names must be unique")
        experiment_axes = tuple(axis for _, _, axis in self.experiments)
        if set(experiment_axes) != set(axis_names):
            raise ValueError("experiments must cover exactly every axis")
        if len(experiment_axes) != len(axis_names):
            raise ValueError("each axis must have exactly one experiment")
        if any(cost <= 0 for _, cost, _ in self.experiments):
            raise ValueError("experiment costs must be positive")

    def iter_worlds(self) -> Iterator[tuple[str, dict[str, str]]]:
        axis_names = tuple(axis for axis, _ in self.axes)
        options = tuple(values for _, values in self.axes)
        for selected in product(*options):
            world = dict(zip(axis_names, selected, strict=True))
            identifier = "|".join(
                f"{axis}={world[axis]}" for axis in axis_names
            )
            yield identifier, world

    def evaluate(self, world: Mapping[str, str]) -> dict[str, object]:
        for axis, options in self.axes:
            if world.get(axis) not in options:
                raise ValueError(f"invalid {axis}: {world.get(axis)!r}")
        adverse_axes = tuple(
            axis
            for axis, _ in self.axes
            if world[axis] == self.adverse_values[axis]
        )
        total_charge = sum(self.charges[axis] for axis in adverse_axes)
        decision = total_charge <= self.threshold
        return {
            "adverse_axes": list(adverse_axes),
            "total_charge": total_charge,
            "threshold": self.threshold,
            "decision": decision,
            "decision_label": (
                self.positive_label if decision else self.negative_label
            ),
        }

    def make_problem(self) -> ActiveDiscoveryProblem:
        rows = tuple(self.iter_worlds())
        hypotheses = tuple(identifier for identifier, _ in rows)
        property_values = {
            identifier: bool(self.evaluate(world)["decision"])
            for identifier, world in rows
        }
        experiments = tuple(
            Experiment(
                name=name,
                cost=cost,
                observations={
                    identifier: world[axis]
                    for identifier, world in rows
                },
            )
            for name, cost, axis in self.experiments
        )
        return ActiveDiscoveryProblem(
            hypotheses=hypotheses,
            property_values=property_values,
            experiments=experiments,
        )


def summarize_case(case: BinaryFinanceCase) -> dict[str, object]:
    problem = case.make_problem()
    basis = problem.exact_fixed_basis()
    if basis is None:
        raise AssertionError(f"{case.name} unexpectedly impossible")
    fixed_cost = sum(
        (experiment.cost for experiment in basis), Fraction(0)
    )
    policy = problem.optimal_policy()
    expected_cost = Fraction(*policy["expected_cost"])
    reduction = Fraction(1) - expected_cost / fixed_cost
    positives = sum(problem.property_values.values())
    return {
        "hypotheses": len(problem.hypotheses),
        "positive_worlds": positives,
        "negative_worlds": len(problem.hypotheses) - positives,
        "conflict_pairs": len(problem.conflict_pairs()),
        "fixed_basis": [experiment.name for experiment in basis],
        "fixed_basis_cost": [fixed_cost.numerator, fixed_cost.denominator],
        "adaptive_worst_cost": policy["worst_cost"],
        "adaptive_expected_cost": policy["expected_cost"],
        "adaptive_reduction": [reduction.numerator, reduction.denominator],
        "root_experiment": policy["tree"].get("experiment"),
    }


CREDIT_UNDERWRITING = BinaryFinanceCase(
    name="credit_underwriting",
    axes=(
        ("cash_flow", ("resilient", "weak")),
        ("leverage", ("moderate", "high")),
        ("collateral", ("liquid", "illiquid")),
        ("concentration", ("diversified", "concentrated")),
        ("covenants", ("protective", "weak")),
    ),
    adverse_values={
        "cash_flow": "weak",
        "leverage": "high",
        "collateral": "illiquid",
        "concentration": "concentrated",
        "covenants": "weak",
    },
    charges={
        "cash_flow": 4,
        "leverage": 3,
        "collateral": 2,
        "concentration": 2,
        "covenants": 1,
    },
    threshold=5,
    experiments=(
        ("cash_flow_quality_audit", Fraction(3), "cash_flow"),
        ("debt_registry_reconciliation", Fraction(1), "leverage"),
        ("independent_collateral_appraisal", Fraction(2), "collateral"),
        ("customer_concentration_audit", Fraction(2), "concentration"),
        ("covenant_legal_review", Fraction(1), "covenants"),
    ),
    positive_label="APPROVE_CREDIT",
    negative_label="DECLINE_OR_RESTRUCTURE",
)


LIQUIDITY_SURVIVAL = BinaryFinanceCase(
    name="liquidity_survival",
    axes=(
        ("collections", ("on_time", "delayed")),
        ("inventory", ("liquid", "stale")),
        ("revolver", ("available", "frozen")),
        ("maturity", ("laddered", "cliff")),
        ("covenant", ("headroom", "tight")),
    ),
    adverse_values={
        "collections": "delayed",
        "inventory": "stale",
        "revolver": "frozen",
        "maturity": "cliff",
        "covenant": "tight",
    },
    charges={
        "collections": 3,
        "inventory": 2,
        "revolver": 4,
        "maturity": 3,
        "covenant": 2,
    },
    threshold=6,
    experiments=(
        ("receivables_collection_audit", Fraction(2), "collections"),
        ("inventory_liquidation_test", Fraction(2), "inventory"),
        ("committed_revolver_confirmation", Fraction(1), "revolver"),
        ("debt_maturity_reconciliation", Fraction(1), "maturity"),
        ("covenant_compliance_recalculation", Fraction(1), "covenant"),
    ),
    positive_label="SURVIVES_90_DAY_STRESS",
    negative_label="LIQUIDITY_REMEDIATION_REQUIRED",
)


PORTFOLIO_MANDATE = BinaryFinanceCase(
    name="portfolio_mandate",
    axes=(
        ("expected_return", ("adequate", "low")),
        ("tail_risk", ("bounded", "severe")),
        ("liquidity", ("liquid", "gated")),
        ("concentration", ("diversified", "concentrated")),
        ("liability_match", ("matched", "mismatched")),
    ),
    adverse_values={
        "expected_return": "low",
        "tail_risk": "severe",
        "liquidity": "gated",
        "concentration": "concentrated",
        "liability_match": "mismatched",
    },
    charges={
        "expected_return": 3,
        "tail_risk": 4,
        "liquidity": 3,
        "concentration": 2,
        "liability_match": 2,
    },
    threshold=6,
    experiments=(
        ("forward_return_assumption_audit", Fraction(2), "expected_return"),
        ("tail_scenario_engine", Fraction(3), "tail_risk"),
        ("liquidity_redemption_test", Fraction(2), "liquidity"),
        ("lookthrough_concentration_audit", Fraction(1), "concentration"),
        ("asset_liability_duration_study", Fraction(2), "liability_match"),
    ),
    positive_label="MANDATE_ADMISSIBLE",
    negative_label="MANDATE_REDESIGN_REQUIRED",
)


BANK_STRESS_RESILIENCE = BinaryFinanceCase(
    name="bank_stress_resilience",
    axes=(
        ("credit_loss", ("contained", "severe")),
        ("deposit_runoff", ("stable", "run")),
        ("market_loss", ("mild", "severe")),
        ("capital", ("robust", "thin")),
        ("liquidity", ("unencumbered", "encumbered")),
    ),
    adverse_values={
        "credit_loss": "severe",
        "deposit_runoff": "run",
        "market_loss": "severe",
        "capital": "thin",
        "liquidity": "encumbered",
    },
    charges={
        "credit_loss": 4,
        "deposit_runoff": 4,
        "market_loss": 2,
        "capital": 3,
        "liquidity": 3,
    },
    threshold=7,
    experiments=(
        ("loan_tape_loss_audit", Fraction(3), "credit_loss"),
        ("deposit_concentration_runoff_study", Fraction(2), "deposit_runoff"),
        ("securities_duration_mark_test", Fraction(1), "market_loss"),
        ("regulatory_capital_reconciliation", Fraction(1), "capital"),
        ("hqla_encumbrance_audit", Fraction(2), "liquidity"),
    ),
    positive_label="STRESS_RESILIENT",
    negative_label="CAPITAL_OR_LIQUIDITY_ACTION_REQUIRED",
)


FINANCE_CASEBOOK: tuple[BinaryFinanceCase, ...] = (
    CREDIT_UNDERWRITING,
    LIQUIDITY_SURVIVAL,
    PORTFOLIO_MANDATE,
    BANK_STRESS_RESILIENCE,
)


def get_case(name: str) -> BinaryFinanceCase:
    for case in FINANCE_CASEBOOK:
        if case.name == name:
            return case
    raise KeyError(name)
