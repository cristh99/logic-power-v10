#!/usr/bin/env bash
set -euo pipefail

mkdir -p tools reports/formal_configs_v1

jar_path="${TLA2TOOLS_JAR:-tools/tla2tools.jar}"
if [ ! -s "$jar_path" ]; then
  curl -L --fail --retry 4 --retry-all-errors \
    https://github.com/tlaplus/tlaplus/releases/download/v1.8.0/tla2tools.jar \
    -o "$jar_path"
fi
echo 'feffd16994db963ad945628cfd03d154c195a468  '"$jar_path" \
  | sha1sum -c -

java -cp "$jar_path" tla2sany.SANY \
  tla_problem_solver_v1/ProblemSolverLifecycle.tla \
  2>&1 | tee reports/problem-solver-sany-v1.log
if grep -Eq 'Semantic errors|\*\*\* Errors:' \
  reports/problem-solver-sany-v1.log; then
  exit 1
fi

for scenario in \
  Exact Search LearnedReady LearnedMissing \
  Unsafe Underspecified Impossible NoBudget; do
  cfg="reports/formal_configs_v1/ProblemSolver${scenario}.cfg"
  cat > "$cfg" <<CFG
CONSTANT Scenario = "${scenario}"
SPECIFICATION Spec
INVARIANT TypeOK
INVARIANT TerminalStatusIff
INVARIANT SolvedHasEvidence
INVARIANT BlockedHasNoSolver
INVARIANT MuZeroNeedsPrerequisites
INVARIANT UnsafeNeverExecutes
INVARIANT TerminalLegitimate
PROPERTY Termination
CFG
  java -cp "$jar_path" tlc2.TLC -workers 1 \
    -config "$cfg" \
    tla_problem_solver_v1/ProblemSolverLifecycle.tla \
    2>&1 | tee "reports/problem-solver-tlc-${scenario}-v1.log"
  grep -q 'Model checking completed. No error has been found.' \
    "reports/problem-solver-tlc-${scenario}-v1.log"
done

if [ ! -x "$HOME/.elan/bin/elan" ]; then
  curl -sSf \
    https://raw.githubusercontent.com/leanprover/elan/master/elan-init.sh \
    | sh -s -- -y --default-toolchain none
fi
export PATH="$HOME/.elan/bin:$PATH"
elan toolchain install leanprover/lean4:v4.33.0-rc1
elan run leanprover/lean4:v4.33.0-rc1 \
  lean ProblemSolverBoundary.lean \
  2>&1 | tee reports/problem-solver-lean-v1.log
if grep -q 'sorryAx' reports/problem-solver-lean-v1.log; then
  echo 'Lean reported sorryAx'
  exit 1
fi
test "$(grep -c 'does not depend on any axioms' \
  reports/problem-solver-lean-v1.log)" -eq 7

python - <<'PY'
import hashlib
import json
from pathlib import Path


def sha256(path: str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


audit = {
    'schema': 'logic-power-problem-solver/formal-audit/1',
    'status': 'verified',
    'tla_sany': True,
    'tlc_scenarios': [
        'Exact',
        'Search',
        'LearnedReady',
        'LearnedMissing',
        'Unsafe',
        'Underspecified',
        'Impossible',
        'NoBudget',
    ],
    'lean_compiled': True,
    'lean_theorems': 7,
    'lean_axioms': 0,
    'lean_sorry_ax': False,
    'tla_sha256': sha256(
        'tla_problem_solver_v1/ProblemSolverLifecycle.tla'
    ),
    'lean_sha256': sha256('ProblemSolverBoundary.lean'),
}
Path('reports/problem-solver-formal-audit-v1.json').write_text(
    json.dumps(audit, indent=2, sort_keys=True) + '\n'
)
PY
