# Logic Power Knowledge–Action Loop v1

LP-KAL formalizes the Tree of Life's strongest invariant: **knowledge is not action, and action is not knowledge**.

## Authority boundary

- **Tree of Life / Classifier:** decides what deserves attention, current state, authority, and feedback.
- **LP-KAL:** enforces typed Knowledge ↔ Actions bridges.
- **Logic Power Problem Solver:** selects information, methods, plans, and capabilities inside authorized work.
- **Plugins:** execute typed capabilities; installation is not authorization.

## Implemented vertical slice

- canonical immutable Knowledge, Action, Evidence, Consequence, Preflight, Receipt, and SolverMandate records;
- action states `ASAP`, `AT_A_DATE`, `DOING`, `DONE`, `SOMEDAY_MAYBE`, and `TRASH`;
- `DOING` requires authorization, a passed preflight, and liveness evidence;
- `DONE` requires verified closure evidence;
- `SOMEDAY_MAYBE` cannot execute;
- Knowledge changes existing work only through an explicit consequence;
- `CREAR` requires an explicit search for an existing destination;
- Knowledge cannot directly claim `DOING` or `DONE`;
- action evidence becomes Knowledge only when verified, marked generalizable, and integrated without changing the verified statement;
- the Problem Solver receives a fingerprint-bound mandate only from authorized executable work;
- Python certificate verifier plus independent Node verifier;
- deterministic demo, rebuild, and tamper rejection.

## Demo lifecycle

```text
verified Knowledge
→ explicit MOVER consequence
→ SOMEDAY_MAYBE → ASAP
→ solver mandate bound to the authorized state
→ passed preflight → DOING
→ verified evidence → DONE
→ exact reusable statement → Knowledge
→ SIN_CAMBIO prevents a duplicate action
```

## Verify

```bash
bash logic_power_knowledge_action_loop_v1/ci_v1.sh
```

## Honest boundary

This slice does not yet prove the entire Tree of Life, preference transformation, universal problem solving, cross-domain superiority, or scientific novelty. Those require the TLA+/Lean refinement layer, a sealed multidomain benchmark, ablations, and comparison against BDI, MAPE-K, Knowledge-to-Action, ReAct, epistemic planning, and proof-carrying execution.

Issue: #89. This branch must remain isolated and unmerged until the scientific and migration gates are explicit.
