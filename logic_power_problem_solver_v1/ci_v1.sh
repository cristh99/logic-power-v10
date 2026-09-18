#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="$PWD${PYTHONPATH:+:$PYTHONPATH}"
rm -rf reports certificates
mkdir -p reports certificates

python -m compileall -q logic_power_problem_solver_v1
python -m unittest discover -s logic_power_problem_solver_v1 -p 'test_*.py' -v

python -m logic_power_problem_solver_v1.run_problem_solver_v1
for case in decision game planning mcts muzero_gate; do
  node logic_power_problem_solver_v1/verify_problem_solver_v1.js \
    "certificates/problem_solver_v1_${case}.json"
done

sha256sum \
  reports/problem_solver_v1.json \
  certificates/problem_solver_v1_decision.json \
  certificates/problem_solver_v1_game.json \
  certificates/problem_solver_v1_planning.json \
  certificates/problem_solver_v1_mcts.json \
  certificates/problem_solver_v1_muzero_gate.json \
  > reports/problem_solver_v1_before.sha256
python -m logic_power_problem_solver_v1.run_problem_solver_v1
sha256sum \
  reports/problem_solver_v1.json \
  certificates/problem_solver_v1_decision.json \
  certificates/problem_solver_v1_game.json \
  certificates/problem_solver_v1_planning.json \
  certificates/problem_solver_v1_mcts.json \
  certificates/problem_solver_v1_muzero_gate.json \
  > reports/problem_solver_v1_after.sha256
cmp reports/problem_solver_v1_before.sha256 \
  reports/problem_solver_v1_after.sha256

python - <<'PY'
import json
from pathlib import Path

path = Path('certificates/problem_solver_v1_decision.json')
certificate = json.loads(path.read_text())
certificate['payload']['result']['action'] = 'tampered'
Path('certificates/problem_solver_v1_tampered.json').write_text(
    json.dumps(certificate, indent=2, sort_keys=True) + '\n'
)
PY
if node logic_power_problem_solver_v1/verify_problem_solver_v1.js \
  certificates/problem_solver_v1_tampered.json; then
  echo 'Node accepted a tampered certificate'
  exit 1
fi

find logic_power_problem_solver_v1 -type d -name '__pycache__' \
  -prune -exec rm -rf {} +
find logic_power_problem_solver_v1 -type f -print0 \
  | sort -z | xargs -0 sha256sum \
  > reports/problem_solver_v1_source_manifest.sha256
sha256sum README_problem_solver_v1.md \
  >> reports/problem_solver_v1_source_manifest.sha256
