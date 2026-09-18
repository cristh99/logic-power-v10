from __future__ import annotations

from fractions import Fraction

from logic_power_v10.active_discovery import (
    ActiveDiscoveryProblem,
    Experiment,
)


def _hypothesis_id(
    capacity_shortage: bool,
    quality_rework: bool,
    supplier_instability: bool,
) -> str:
    return (
        f"c{int(capacity_shortage)}_"
        f"q{int(quality_rework)}_"
        f"s{int(supplier_instability)}"
    )


HYPOTHESIS_SEMANTICS: dict[str, dict[str, bool]] = {
    _hypothesis_id(capacity, quality, supplier): {
        "capacity_shortage": capacity,
        "quality_rework": quality,
        "supplier_instability": supplier,
    }
    for capacity in (False, True)
    for quality in (False, True)
    for supplier in (False, True)
}


def _observations(
    factor: str,
    positive: str,
    negative: str,
) -> dict[str, str]:
    return {
        hypothesis: positive if world[factor] else negative
        for hypothesis, world in HYPOTHESIS_SEMANTICS.items()
    }


def make_capex_gate_problem(
    *, include_supplier_trace: bool = True
) -> ActiveDiscoveryProblem:
    """Compile a finite logistics gate for capacity-expansion decisions.

    The proposed capital expansion is valid only in the world where:

    * the candidate station is genuinely capacity constrained;
    * excess rework is not the limiting mechanism; and
    * supplier instability is not the limiting mechanism.

    The gate deliberately tests cheaper invalidating mechanisms before the
    expensive capacity stress pilot. Logic Power v10 proves whether the
    available experiments are sufficient and synthesizes the exact minimum
    policy or an indistinguishability obstruction.
    """

    hypotheses = tuple(sorted(HYPOTHESIS_SEMANTICS))
    property_values = {
        hypothesis: (
            world["capacity_shortage"]
            and not world["quality_rework"]
            and not world["supplier_instability"]
        )
        for hypothesis, world in HYPOTHESIS_SEMANTICS.items()
    }

    experiments: list[Experiment] = [
        Experiment(
            name="capacity_stress_pilot",
            cost=Fraction(4),
            observations=_observations(
                "capacity_shortage",
                "capacity_constrained",
                "capacity_adequate",
            ),
        ),
        Experiment(
            name="first_pass_yield_audit",
            cost=Fraction(1),
            observations=_observations(
                "quality_rework",
                "rework_excess",
                "first_pass_yield_ok",
            ),
        ),
    ]
    if include_supplier_trace:
        experiments.append(
            Experiment(
                name="supplier_continuity_trace",
                cost=Fraction(1),
                observations=_observations(
                    "supplier_instability",
                    "supplier_unstable",
                    "supplier_stable",
                ),
            )
        )

    return ActiveDiscoveryProblem(
        hypotheses=hypotheses,
        property_values=property_values,
        experiments=tuple(experiments),
    )
