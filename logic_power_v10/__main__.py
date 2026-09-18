from __future__ import annotations

import sys

from logic_power_v10 import verify_logic_power_v10

USAGE = "usage: python -m logic_power_v10 verify CERTIFICATE.json"


def main() -> int:
    args = sys.argv[1:]
    if args in (["-h"], ["--help"]):
        print(USAGE)
        return 0
    if len(args) != 2 or args[0] != "verify":
        print(USAGE, file=sys.stderr)
        return 2
    sys.argv = [sys.argv[0], args[1]]
    return verify_logic_power_v10.main()


if __name__ == "__main__":
    raise SystemExit(main())
