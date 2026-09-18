"""Proof-carrying financial decision cases built on Logic Power v10."""

from .capital_allocation import (
    AXES,
    EXPERIMENT_COSTS,
    iter_capital_allocation_worlds,
    make_capital_allocation_problem,
    make_hidden_liability_obstruction,
    project_metrics,
)
from .casebook import (
    BANK_STRESS_RESILIENCE,
    CREDIT_UNDERWRITING,
    FINANCE_CASEBOOK,
    LIQUIDITY_SURVIVAL,
    PORTFOLIO_MANDATE,
    BinaryFinanceCase,
    get_case,
    summarize_case,
)

__all__ = [
    "AXES",
    "EXPERIMENT_COSTS",
    "BANK_STRESS_RESILIENCE",
    "CREDIT_UNDERWRITING",
    "FINANCE_CASEBOOK",
    "LIQUIDITY_SURVIVAL",
    "PORTFOLIO_MANDATE",
    "BinaryFinanceCase",
    "get_case",
    "iter_capital_allocation_worlds",
    "make_capital_allocation_problem",
    "make_hidden_liability_obstruction",
    "project_metrics",
    "summarize_case",
]
