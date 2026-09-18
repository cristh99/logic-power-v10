"""Logic Power v10: proof-carrying active discovery over finite hypotheses."""

from .active_discovery import (
    ActiveDiscoveryProblem,
    Experiment,
    MonitorStatus,
    make_impossible_demo,
    make_or_problem,
)
from .certificate import build_certificate, verify_certificate

__all__ = [
    "ActiveDiscoveryProblem",
    "Experiment",
    "MonitorStatus",
    "build_certificate",
    "verify_certificate",
    "make_impossible_demo",
    "make_or_problem",
]
