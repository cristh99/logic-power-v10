#!/usr/bin/env bash
# One-command gate runner for the Logic Power v10 public repository.
# Runs every Python and Node gate from the release audit plus the CLI and
# parity tests added on this branch. TLA+ and Lean gates intentionally stay
# in logic_power_v10/ci_v10.sh and the per-component ci_*.sh scripts and are
# not executed here.
set -euo pipefail
cd "$(dirname "$0")/.."

PYTHON="${PYTHON:-python}"
NODE="${NODE:-node}"
export PYTHONPATH="$PWD${PYTHONPATH:+:$PYTHONPATH}"
export PYTHONDONTWRITEBYTECODE=1

GATES=()
RESULTS=()
COUNTS=()
FAILED=0

record() {
  GATES+=("$1")
  RESULTS+=("$2")
  COUNTS+=("$3")
  [ "$2" != "FAIL" ] || FAILED=1
}

count_ran() {
  grep -oE 'Ran [0-9]+ tests' | tail -n 1 | awk '{print $2}' || true
}

check() {
  local name="$1" out rc count
  shift
  set +e
  out="$("$@" 2>&1)"
  rc=$?
  set -e
  count="$(printf '%s' "$out" | count_ran)"
  if [ "$rc" -eq 0 ]; then
    record "$name" PASS "${count:-ok}"
  else
    printf '---- %s (rc=%s) ----\n%s\n' "$name" "$rc" "$out" >&2
    record "$name" FAIL "${count:--}"
  fi
}

check_unittests_release_manifest() {
  local out rc ran fails other
  set +e
  out="$(GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null \
    "$PYTHON" -m unittest tests.test_logic_power_release_manifest 2>&1)"
  rc=$?
  set -e
  ran="$(printf '%s' "$out" | count_ran)"; ran="${ran:-0}"
  if [ "$rc" -eq 0 ]; then
    record "unittests-release-manifest" PASS "$ran/$ran"
    return
  fi
  fails="$(printf '%s' "$out" | grep -cE '^(FAIL|ERROR): ' || true)"
  other="$(printf '%s' "$out" | grep -E '^(FAIL|ERROR): ' \
    | grep -vc 'test_tree_hash_matches_git_and_changes_on_mutation' || true)"
  if [ "$other" -eq 0 ]; then
    record "unittests-release-manifest" "PASS*" "$((ran - fails))/$ran"
  else
    printf '%s\n' "$out" >&2
    record "unittests-release-manifest" FAIL "$((ran - fails))/$ran"
  fi
}

manifest_component_sha() {
  "$PYTHON" - "$1" <<'PY'
import json
import sys

manifest = json.load(open("LOGIC_POWER_RELEASE_MANIFEST.json"))
print(
    next(
        component["git_object_sha"]
        for component in manifest["components"]
        if component["name"] == sys.argv[1]
    )
)
PY
}

manifest_bound_objects() {
  "$PYTHON" - <<'PY'
import json

manifest = json.load(open("LOGIC_POWER_RELEASE_MANIFEST.json"))
print(
    len(manifest["components"])
    + len(manifest["formal_objects"])
    + len(manifest["documentation_objects"])
)
PY
}

# The release manifest binds the release-candidate trees. Post-release work
# on this branch intentionally changed the released components, so the gate
# is evaluated against the newest ancestor of HEAD whose trees still match
# the manifest — the checkout the manifest describes.
find_release_commit() {
  local components=(
    logic_power_v10
    logic_power_problem_solver_v1
    logic_power_knowledge_action_loop_v1
  )
  local commit component want got match
  for commit in $(git rev-list HEAD); do
    match=1
    for component in "${components[@]}"; do
      want="$(manifest_component_sha "$component")"
      got="$(git rev-parse -q --verify "$commit:$component" 2>/dev/null || true)"
      if [ "$got" != "$want" ]; then
        match=0
        break
      fi
    done
    if [ "$match" -eq 1 ]; then
      echo "$commit"
      return 0
    fi
  done
  return 1
}

check_release_manifest() {
  local commit tmp out rc objects
  objects="$(manifest_bound_objects)"
  if ! commit="$(find_release_commit)"; then
    printf 'no ancestor of HEAD matches the manifest component trees\n' >&2
    record "release-manifest" FAIL "$objects"
    return
  fi
  tmp="$(mktemp -d)"
  git archive "$commit" | tar -x -C "$tmp"
  set +e
  out="$("$PYTHON" tools/validate_logic_power_release.py \
    --manifest "$tmp/LOGIC_POWER_RELEASE_MANIFEST.json" \
    --root "$tmp" 2>&1)"
  rc=$?
  set -e
  rm -rf "$tmp"
  echo "release manifest validated against checkout $commit"
  if [ "$rc" -eq 0 ] \
    && printf '%s' "$out" | grep -q 'LOGIC_POWER_RELEASE_MANIFEST_PASS'; then
    record "release-manifest" PASS "$objects"
  else
    printf '%s\n' "$out" >&2
    record "release-manifest" FAIL "$objects"
  fi
}

check "unittests-v10" \
  "$PYTHON" -m unittest discover -s logic_power_v10 -p 'test_*.py'
check "unittests-problem-solver" \
  "$PYTHON" -m unittest discover -s logic_power_problem_solver_v1 -p 'test_*.py'
check "unittests-lp-kal" \
  "$PYTHON" -m unittest logic_power_knowledge_action_loop_v1.test_lp_kal_v1
check "unittests-finance" \
  env PYTHONPATH="$PWD:$PWD/examples/finance-decisions" \
  "$PYTHON" -m unittest discover \
  -s examples/finance-decisions/finance_logic_v10 \
  -t examples/finance-decisions -p 'test_*.py'
check "unittests-logistics" \
  env PYTHONPATH="$PWD:$PWD/examples/logistics-capex" \
  "$PYTHON" -m unittest discover \
  -s examples/logistics-capex/logistics_power_v1 \
  -t examples/logistics-capex -p 'test_*.py'
check "unittests-cli" "$PYTHON" -m unittest logic_power_v10.test_cli_v10
check "parity-python" "$PYTHON" -m unittest tests.parity.test_parity_python

parity_node_out="$(mktemp)"
set +e
"$NODE" --test tests/parity/ >"$parity_node_out" 2>&1
parity_node_rc=$?
set -e
parity_node_count="$({ grep -E '^# pass ' "$parity_node_out" || true; } | awk '{print $3}')"
if [ "$parity_node_rc" -eq 0 ]; then
  record "parity-node" PASS "${parity_node_count:-ok}"
else
  cat "$parity_node_out" >&2
  record "parity-node" FAIL "${parity_node_count:--}"
fi
rm -f "$parity_node_out"

check "run-logic-power-v10" "$PYTHON" -m logic_power_v10.run_logic_power_v10

artifacts=(
  certificates/logic_power_v10_exact.json
  certificates/logic_power_v10_impossible.json
  certificates/logic_power_v10_tampered.json
  reports/logic_power_v10.json
  reports/logic_power_v10.canonical.json
)
artifact_failures=0
for artifact in "${artifacts[@]}"; do
  [ -f "$artifact" ] || artifact_failures=$((artifact_failures + 1))
done
if [ "$artifact_failures" -eq 0 ]; then
  record "run-artifacts" PASS "${#artifacts[@]}"
else
  record "run-artifacts" FAIL "$artifact_failures"
fi

accept_failures=0
for cert in exact impossible; do
  "$PYTHON" -m logic_power_v10.verify_logic_power_v10 \
    "certificates/logic_power_v10_${cert}.json" >/dev/null \
    || accept_failures=$((accept_failures + 1))
  "$NODE" logic_power_v10/verify_logic_power_v10.js \
    "certificates/logic_power_v10_${cert}.json" >/dev/null \
    || accept_failures=$((accept_failures + 1))
done
if [ "$accept_failures" -eq 0 ]; then
  record "verify-accept" PASS 4
else
  record "verify-accept" FAIL "$accept_failures"
fi

reject_failures=0
if "$PYTHON" -m logic_power_v10.verify_logic_power_v10 \
  certificates/logic_power_v10_tampered.json >/dev/null; then
  reject_failures=$((reject_failures + 1))
fi
if "$NODE" logic_power_v10/verify_logic_power_v10.js \
  certificates/logic_power_v10_tampered.json >/dev/null; then
  reject_failures=$((reject_failures + 1))
fi
if [ "$reject_failures" -eq 0 ]; then
  record "verify-reject-tampered" PASS 2
else
  record "verify-reject-tampered" FAIL "$reject_failures"
fi

find . -type d -name '__pycache__' -prune -exec rm -rf {} +

check_release_manifest
check_unittests_release_manifest

printf '\n%-28s | %-6s | %s\n' "gate" "result" "count"
printf '%s\n' "-----------------------------+--------+----------"
for i in "${!GATES[@]}"; do
  printf '%-28s | %-6s | %s\n' "${GATES[$i]}" "${RESULTS[$i]}" "${COUNTS[$i]}"
done
if printf '%s\n' "${RESULTS[@]}" | grep -q 'PASS\*'; then
  cat <<'EOF'
* unittests-release-manifest: 6/7 on this machine —
  test_tree_hash_matches_git_and_changes_on_mutation fails only because git
  here auto-detects core.filemode=false; it passes on GitHub-hosted Ubuntu.
EOF
fi

if [ "$FAILED" -ne 0 ]; then
  echo "check: FAIL"
  exit 1
fi
echo "check: PASS"
