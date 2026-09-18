"""Evidence table: exact fixed basis vs dual lower bound.

Builds the repository's own applied problems (logistics capex with and
without the supplier trace, the four finance casebook cases, capital
allocation and the hidden-liability obstruction) plus the canonical
``or_8_exact`` and prints a Markdown table comparing the exact minimum
basis cost with the deterministic dual lower bound.
"""
from __future__ import annotations

import sys
import time
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for extra in (
    "examples/finance-decisions",
    "examples/logistics-capex",
):
    path = str(ROOT / extra)
    if path not in sys.path:
        sys.path.insert(0, path)

from logic_power_v10.active_discovery import (  # noqa: E402
    ActiveDiscoveryProblem,
    make_or_problem,
)

from logic_power_fixed_basis_bound_v1.bounds import (  # noqa: E402
    dual_lower_bound,
    forced_experiments,
)

from finance_logic_v10.capital_allocation import (  # noqa: E402
    make_capital_allocation_problem,
    make_hidden_liability_obstruction,
)
from finance_logic_v10.casebook import FINANCE_CASEBOOK  # noqa: E402
from logistics_power_v1.capex_gate import (  # noqa: E402
    make_capex_gate_problem,
)

REPEATS = 5


def _timed_ns(func, repeats: int = REPEATS) -> tuple[object, int]:
    best: int | None = None
    result = None
    for _ in range(repeats):
        start = time.perf_counter_ns()
        result = func()
        elapsed = time.perf_counter_ns() - start
        if best is None or elapsed < best:
            best = elapsed
    return result, best


def _millis(nanoseconds: int) -> str:
    whole, rest = divmod(nanoseconds, 1_000_000)
    return f"{whole}.{rest // 1000:03d}"


def _fraction_text(value: Fraction | None) -> str:
    if value is None:
        return "—"
    if value.denominator == 1:
        return str(value.numerator)
    return f"{value.numerator}/{value.denominator}"


def _row(
    name: str, problem: ActiveDiscoveryProblem
) -> list[str]:
    basis, basis_ns = _timed_ns(problem.exact_fixed_basis)
    dual, dual_ns = _timed_ns(lambda: dual_lower_bound(problem))
    conflicts = len(problem.conflict_pairs())
    if basis is None:
        return [
            name,
            str(len(problem.hypotheses)),
            str(len(problem.experiments)),
            str(conflicts),
            "—",
            "—",
            "—",
            "—",
            _millis(basis_ns),
            _millis(dual_ns),
        ]
    basis_cost = sum(
        (experiment.cost for experiment in basis), Fraction(0)
    )
    dual_value = dual[1] if dual is not None else None
    forced = forced_experiments(problem)
    return [
        name,
        str(len(problem.hypotheses)),
        str(len(problem.experiments)),
        str(conflicts),
        _fraction_text(basis_cost),
        _fraction_text(dual_value),
        "true" if dual_value == basis_cost else "false",
        str(0 if forced is None else len(forced)),
        _millis(basis_ns),
        _millis(dual_ns),
    ]


def main() -> None:
    cases: list[tuple[str, ActiveDiscoveryProblem]] = [
        ("or_8_exact", make_or_problem(8)),
        (
            "capex_gate",
            make_capex_gate_problem(),
        ),
        (
            "capex_gate_no_supplier_trace",
            make_capex_gate_problem(include_supplier_trace=False),
        ),
    ]
    cases.extend(
        (case.name, case.make_problem()) for case in FINANCE_CASEBOOK
    )
    cases.append(
        ("capital_allocation", make_capital_allocation_problem())
    )
    cases.append(
        (
            "hidden_liability_obstruction",
            make_hidden_liability_obstruction(),
        )
    )

    header = (
        "| caso | |H| | |E| | parejas | costo base | valor dual "
        "| tight | forzados | ms exact_fixed_basis | ms dual_lower_bound |"
    )
    divider = (
        "|---|---|---|---|---|---|---|---|---|---|---|"
    )
    print(header)
    print(divider)
    for name, problem in cases:
        print("| " + " | ".join(_row(name, problem)) + " |")


if __name__ == "__main__":
    main()
