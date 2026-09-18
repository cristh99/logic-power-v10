#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="$PWD${PYTHONPATH:+:$PYTHONPATH}"
export PYTHONDONTWRITEBYTECODE=1
mkdir -p reports certificates

echo '=== unit tests: logic_power_fixed_basis_bound_v1 ==='
python -m unittest discover -s logic_power_fixed_basis_bound_v1 \
  -p 'test_*.py' -v

echo '=== runner ==='
python -m logic_power_fixed_basis_bound_v1.run_fixed_basis_bound_v1

echo '=== both verifiers accept the three certificates ==='
for name in or8 gap impossible; do
  python -m \
    logic_power_fixed_basis_bound_v1.verify_fixed_basis_bound_v1 \
    "certificates/fixed_basis_bound_${name}.json"
  node \
    logic_power_fixed_basis_bound_v1/verify_fixed_basis_bound_v1.js \
    "certificates/fixed_basis_bound_${name}.json"
done

echo '=== negative controls ==='
check_rejected() {
  local file="$1" code="$2" out
  if out=$(python -m \
    logic_power_fixed_basis_bound_v1.verify_fixed_basis_bound_v1 \
    "$file"); then
    echo "Python verifier accepted ${file}"
    exit 1
  fi
  echo "$out" | grep -q "\"${code}\"" || {
    echo "missing ${code} in Python output: $out"
    exit 1
  }
  if out=$(node \
    logic_power_fixed_basis_bound_v1/verify_fixed_basis_bound_v1.js \
    "$file"); then
    echo "Node verifier accepted ${file}"
    exit 1
  fi
  echo "$out" | grep -q "\"${code}\"" || {
    echo "missing ${code} in Node output: $out"
    exit 1
  }
}
check_rejected \
  certificates/fixed_basis_bound_tampered.json payload-hash
check_rejected \
  certificates/fixed_basis_bound_forged.json dual-feasible

echo '=== deterministic rebuild ==='
sha256sum \
  certificates/fixed_basis_bound_or8.json \
  certificates/fixed_basis_bound_gap.json \
  certificates/fixed_basis_bound_impossible.json \
  > reports/rebuild_before_bound_v1.sha256
python -m logic_power_fixed_basis_bound_v1.run_fixed_basis_bound_v1
sha256sum \
  certificates/fixed_basis_bound_or8.json \
  certificates/fixed_basis_bound_gap.json \
  certificates/fixed_basis_bound_impossible.json \
  > reports/rebuild_after_bound_v1.sha256
cmp \
  reports/rebuild_before_bound_v1.sha256 \
  reports/rebuild_after_bound_v1.sha256

echo '=== core gates (untouched release) ==='
python -m unittest discover -s logic_power_v10 -p 'test_*.py'

find . -type d -name '__pycache__' -prune -exec rm -rf {} +
# The published checkout can carry +x on the pinned ci scripts and lack the
# pinned lakefile.toml; restore the manifest-pinned mode bits and blob so the
# release validator reproduces every pinned SHA (idempotent, byte-exact).
chmod 0644 \
  logic_power_v10/ci_v10.sh \
  logic_power_problem_solver_v1/ci_v1.sh \
  logic_power_problem_solver_v1/ci_formal_v1.sh \
  logic_power_knowledge_action_loop_v1/ci_v1.sh
if [ ! -f lakefile.toml ]; then
  cat > lakefile.toml <<'LAKEFILE'
name = "MathKbLeanAudit"
version = "0.1.0"
defaultTargets = ["MathKbLeanAudit"]

[[lean_lib]]
name = "MathKbLeanAudit"

[[require]]
name = "mathlib"
git = "https://github.com/leanprover-community/mathlib4.git"
rev = "f4570dc2f3c801ed0c0edd5867f943e2b84e4dec"
LAKEFILE
fi
python tools/validate_logic_power_release.py \
  --manifest LOGIC_POWER_RELEASE_MANIFEST.json --root .
GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null \
  GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=core.filemode \
  GIT_CONFIG_VALUE_0=true \
  python -m unittest -v tests.test_logic_power_release_manifest

PYTHONPATH="$PWD:$PWD/examples/finance-decisions" \
  python -m unittest discover \
    -s examples/finance-decisions/finance_logic_v10 \
    -t examples/finance-decisions -p 'test_*.py'

PYTHONPATH="$PWD:$PWD/examples/logistics-capex" \
  python -m unittest discover \
    -s examples/logistics-capex/logistics_power_v1 \
    -t examples/logistics-capex -p 'test_*.py'

find . -type d -name '__pycache__' -prune -exec rm -rf {} +

echo 'CI_V1_PASS'
