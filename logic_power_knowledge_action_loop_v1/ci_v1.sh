#!/usr/bin/env bash
set -euo pipefail
export PYTHONPATH="$PWD${PYTHONPATH:+:$PYTHONPATH}"
rm -rf reports certificates
mkdir -p reports certificates
python -m compileall -q logic_power_knowledge_action_loop_v1
python -m unittest discover -s logic_power_knowledge_action_loop_v1 -p 'test_*.py' -v
python -m logic_power_knowledge_action_loop_v1.run_demo
node logic_power_knowledge_action_loop_v1/verify_lp_kal_v1.js certificates/lp_kal_v1_demo.json
sha256sum reports/lp_kal_v1_state.json certificates/lp_kal_v1_demo.json > reports/lp_kal_v1_before.sha256
python -m logic_power_knowledge_action_loop_v1.run_demo
sha256sum reports/lp_kal_v1_state.json certificates/lp_kal_v1_demo.json > reports/lp_kal_v1_after.sha256
cmp reports/lp_kal_v1_before.sha256 reports/lp_kal_v1_after.sha256
python - <<'PY'
import json
from pathlib import Path
p=Path('certificates/lp_kal_v1_demo.json')
c=json.loads(p.read_text())
c['payload']['result']['action_count']=999
Path('certificates/lp_kal_v1_tampered.json').write_text(json.dumps(c,sort_keys=True)+'\n')
PY
if node logic_power_knowledge_action_loop_v1/verify_lp_kal_v1.js certificates/lp_kal_v1_tampered.json; then
  echo 'tampered certificate accepted'; exit 1
fi
python - <<'PY'
from logic_power_knowledge_action_loop_v1.model import canonical_json
for value in ({'x':1.5},{'x':2**53}):
    try: canonical_json(value)
    except (TypeError,ValueError): pass
    else: raise SystemExit('unsafe numeric value accepted')
PY
find logic_power_knowledge_action_loop_v1 -type d -name '__pycache__' -prune -exec rm -rf {} +
find logic_power_knowledge_action_loop_v1 -type f -print0 | sort -z | xargs -0 sha256sum > reports/lp_kal_v1_source_manifest.sha256
sha256sum README_lp_kal_v1.md >> reports/lp_kal_v1_source_manifest.sha256
