from __future__ import annotations

from fractions import Fraction
from itertools import product
from typing import Iterator, Mapping

from logic_power_v10.active_discovery import ActiveDiscoveryProblem, Experiment


AXES: tuple[tuple[str, tuple[str, str]], ...] = (
    ("demand", ("contracted", "uncontracted")),
    ("capex", ("fixed", "overrun")),
    ("funding", ("committed", "expensive")),
    ("working_capital", ("normal", "stressed")),
    ("terminal", ("disciplined", "fragile")),
)

EXPERIMENT_COSTS: Mapping[str, Fraction] = {
    "signed_customer_contracts": Fraction(2),
    "fixed_price_vendor_quote": Fraction(3),
    "committed_financing_term_sheet": Fraction(1),
    "working_capital_quality_audit": Fraction(2),
    "terminal_reinvestment_audit": Fraction(2),
}


def _fraction_data(value: Fraction) -> list[int]:
    return [value.numerator, value.denominator]


def _world_id(world: Mapping[str, str]) -> str:
    return "|".join(f"{axis}={world[axis]}" for axis, _ in AXES)


def iter_capital_allocation_worlds() -> Iterator[tuple[str, dict[str, str]]]:
    names = tuple(axis for axis, _ in AXES)
    values = tuple(options for _, options in AXES)
    for selected in product(*values):
        world = dict(zip(names, selected, strict=True))
        yield _world_id(world), world


def project_metrics(world: Mapping[str, str]) -> dict[str, object]:
    for axis, options in AXES:
        if world.get(axis) not in options:
            raise ValueError(f"invalid {axis}: {world.get(axis)!r}")

    annual_fcf = Fraction(300 if world["demand"] == "contracted" else 150)
    capex = Fraction(700 if world["capex"] == "fixed" else 950)
    discount_rate = (
        Fraction(1, 10)
        if world["funding"] == "committed"
        else Fraction(9, 50)
    )
    working_capital = Fraction(
        80 if world["working_capital"] == "normal" else 220
    )
    terminal_value = Fraction(
        500 if world["terminal"] == "disciplined" else -50
    )

    npv = -capex - working_capital
    for period in range(1, 5):
        npv += annual_fcf / (1 + discount_rate) ** period
    npv += (terminal_value + working_capital) / (
        1 + discount_rate
    ) ** 4

    liquidity_headroom = (
        Fraction(500)
        - working_capital
        - max(capex - Fraction(700), Fraction(0))
    )
    approve = npv > 0 and liquidity_headroom >= 100

    return {
        "annual_fcf": _fraction_data(annual_fcf),
        "capex": _fraction_data(capex),
        "discount_rate": _fraction_data(discount_rate),
        "working_capital": _fraction_data(working_capital),
        "terminal_value": _fraction_data(terminal_value),
        "npv": _fraction_data(npv),
        "liquidity_headroom": _fraction_data(liquidity_headroom),
        "approve": approve,
    }


def make_capital_allocation_problem() -> ActiveDiscoveryProblem:
    rows = tuple(iter_capital_allocation_worlds())
    hypotheses = tuple(identifier for identifier, _ in rows)
    property_values = {
        identifier: bool(project_metrics(world)["approve"])
        for identifier, world in rows
    }
    prior = {
        identifier: Fraction(1, len(hypotheses))
        for identifier in hypotheses
    }

    experiments = (
        Experiment(
            name="signed_customer_contracts",
            cost=EXPERIMENT_COSTS["signed_customer_contracts"],
            observations={
                identifier: world["demand"] for identifier, world in rows
            },
        ),
        Experiment(
            name="fixed_price_vendor_quote",
            cost=EXPERIMENT_COSTS["fixed_price_vendor_quote"],
            observations={
                identifier: world["capex"] for identifier, world in rows
            },
        ),
        Experiment(
            name="committed_financing_term_sheet",
            cost=EXPERIMENT_COSTS["committed_financing_term_sheet"],
            observations={
                identifier: world["funding"] for identifier, world in rows
            },
        ),
        Experiment(
            name="working_capital_quality_audit",
            cost=EXPERIMENT_COSTS["working_capital_quality_audit"],
            observations={
                identifier: world["working_capital"]
                for identifier, world in rows
            },
        ),
        Experiment(
            name="terminal_reinvestment_audit",
            cost=EXPERIMENT_COSTS["terminal_reinvestment_audit"],
            observations={
                identifier: world["terminal"] for identifier, world in rows
            },
        ),
    )
    return ActiveDiscoveryProblem(
        hypotheses=hypotheses,
        property_values=property_values,
        experiments=experiments,
        prior=prior,
    )


def make_hidden_liability_obstruction() -> ActiveDiscoveryProblem:
    hypotheses = ("clean_balance_sheet", "hidden_tax_claim")
    flat_observations = {
        "clean_balance_sheet": "reported_clean",
        "hidden_tax_claim": "reported_clean",
    }
    experiments = (
        Experiment(
            name="bank_statement_reconciliation",
            cost=Fraction(1),
            observations=flat_observations,
        ),
        Experiment(
            name="quality_of_earnings",
            cost=Fraction(2),
            observations=flat_observations,
        ),
        Experiment(
            name="signed_customer_contracts",
            cost=Fraction(2),
            observations=flat_observations,
        ),
    )
    return ActiveDiscoveryProblem(
        hypotheses=hypotheses,
        property_values={
            "clean_balance_sheet": True,
            "hidden_tax_claim": False,
        },
        experiments=experiments,
    )
