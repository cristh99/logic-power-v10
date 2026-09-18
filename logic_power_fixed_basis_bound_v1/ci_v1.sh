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
# Release-manifest gate. The full checkout validation (--root .) is KNOWN to
# fail on the published tree for two pre-existing reasons that this extension
# must not paper over: lakefile.toml (pinned blob 2275046c...) was deliberately
# left out of the publication, and four pinned ci_*.sh scripts carry mode 0755
# where the pinned trees expect 0644 (invisible on Windows, visible on Linux).
# A gate must never rewrite the tree it checks, so only the manifest contract
# is validated here; see DEVIN_LP10_MATH_REPORT.md (reviewer note).
python tools/validate_logic_power_release.py \
  --manifest LOGIC_POWER_RELEASE_MANIFEST.json --manifest-only
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
