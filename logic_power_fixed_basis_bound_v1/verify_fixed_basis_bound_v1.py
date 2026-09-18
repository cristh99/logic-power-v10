from __future__ import annotations

import json
import sys
from pathlib import Path

from logic_power_fixed_basis_bound_v1.certificate import (
    verify_bound_certificate,
)


def main() -> int:
    if len(sys.argv) != 2:
        print(
            "usage: verify_fixed_basis_bound_v1.py CERTIFICATE.json",
            file=sys.stderr,
        )
        return 2
    path = Path(sys.argv[1])
    try:
        certificate = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(
            json.dumps(
                {
                    "valid": False,
                    "errors": [f"read:{type(exc).__name__}"],
                }
            )
        )
        return 1
    errors = verify_bound_certificate(certificate)
    print(
        json.dumps(
            {"valid": not errors, "errors": errors}, sort_keys=True
        )
    )
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
