# Logic Power Core RC1

This branch is a **minimal, unmerged release candidate** assembled from immutable Git objects already verified in their source pull requests.

## Included

- Logic Power v10 — active information planning and exact impossibility certificates.
- Logic Power Problem Solver v1 — typed problem representation, solver routing, exact decision/planning methods and certificates.
- LP-KAL v1 — typed Knowledge ↔ Actions bridges, authority, evidence and feedback.
- Direct TLA+/Lean boundaries and source documentation required to inspect those components.

## Claim boundary

- v10 is `VERIFIED_SCOPED`, not a global Logic score.
- Problem Solver is `INTERNALLY_VERIFIED`; external utility is not established.
- LP-KAL is internally verified, but its V4 structured calibration tied an equally protected monolithic baseline.
- This RC improves operability, lineage and reviewability. It does **not** prove universal solving, production readiness, scientific priority or additional external power.

## Isolation

The RC starts from an immutable `main` commit and reuses existing Git tree/blob objects. It does not merge, rebase or edit any active agent branch. It adds no workflow and requires no paid execution.

## Verification

Run:

```bash
python tools/validate_logic_power_release.py --manifest LOGIC_POWER_RELEASE_MANIFEST.json --root .
python -m unittest -v tests/test_logic_power_release_manifest.py
python -m unittest -v logic_power_v10/test_logic_power_v10.py
python -m unittest discover -v -s logic_power_problem_solver_v1 -p 'test_*.py'
python -m unittest -v logic_power_knowledge_action_loop_v1/test_lp_kal_v1.py
```

Node verifiers remain available inside each component. TLA+/Lean objects preserve their source hashes and source-PR lineage.
