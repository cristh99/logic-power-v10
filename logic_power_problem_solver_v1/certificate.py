"""Deterministic proof-carrying terminal certificates."""
from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

from .problem_ir import MAX_SAFE_INTEGER, TerminalStatus


SCHEMA = "logic-power-problem-solver/certificate/1"


def _validate_exact_json(value: Any, path: str = "payload") -> None:
    if value is None or isinstance(value, (str, bool)):
        return
    if isinstance(value, int):
        if abs(value) > MAX_SAFE_INTEGER:
            raise ValueError(
                f"{path} integer exceeds the cross-runtime safe range; "
                "encode it as a decimal string"
            )
        return
    if isinstance(value, float):
        raise TypeError(
            f"{path} contains a float; encode approximate values as "
            "decimal strings or certified interval objects"
        )
    if isinstance(value, list):
        for index, item in enumerate(value):
            _validate_exact_json(item, f"{path}[{index}]")
        return
    if isinstance(value, Mapping):
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError(f"{path} keys must be strings")
            _validate_exact_json(item, f"{path}.{key}")
        return
    raise TypeError(
        f"{path} contains unsupported value {type(value).__name__}"
    )


def _canonical_json(value: Any) -> str:
    _validate_exact_json(value)
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _digest(value: Any) -> str:
    return hashlib.sha256(
        _canonical_json(value).encode("utf-8")
    ).hexdigest()


def build_certificate(
    *,
    problem_fingerprint: str,
    routing_fingerprint: str,
    status: TerminalStatus,
    result: Mapping[str, Any],
    evidence: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(status, TerminalStatus):
        raise TypeError("status must be TerminalStatus")
    for name, value in (
        ("problem_fingerprint", problem_fingerprint),
        ("routing_fingerprint", routing_fingerprint),
    ):
        if len(value) != 64 or any(
            char not in "0123456789abcdef" for char in value
        ):
            raise ValueError(f"{name} must be a lowercase SHA-256 digest")
    payload = {
        "problem_fingerprint": problem_fingerprint,
        "routing_fingerprint": routing_fingerprint,
        "status": status.value,
        "result": dict(result),
        "evidence": dict(evidence),
    }
    _validate_exact_json(payload)
    return {
        "schema": SCHEMA,
        "payload": payload,
        "payload_sha256": _digest(payload),
    }


def verify_certificate(certificate: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    if certificate.get("schema") != SCHEMA:
        errors.append("schema")
    payload = certificate.get("payload")
    if not isinstance(payload, Mapping):
        return errors + ["payload"]
    try:
        expected_digest = _digest(payload)
    except (TypeError, ValueError):
        expected_digest = None
        errors.append("payload-canonical-json")
    if (
        expected_digest is not None
        and certificate.get("payload_sha256") != expected_digest
    ):
        errors.append("payload-hash")
    try:
        TerminalStatus(str(payload.get("status")))
    except ValueError:
        errors.append("status")
    for key in ("problem_fingerprint", "routing_fingerprint"):
        value = payload.get(key)
        if (
            not isinstance(value, str)
            or len(value) != 64
            or any(char not in "0123456789abcdef" for char in value)
        ):
            errors.append(key)
    return errors
