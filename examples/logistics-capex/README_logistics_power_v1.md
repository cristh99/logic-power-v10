# Logistics Power Compiler v1 — Logic Power v10 applied

## Core claim

A logistics intervention must not be selected from an ambiguous diagnosis. This compiler turns a finite set of competing operational worlds into one of two proof-carrying outputs:

1. an exact minimum-cost experiment policy that decides whether the intervention is valid; or
2. an exact obstruction showing two opposite-decision worlds that every currently allowed probe observes identically.

It instantiates the verified separation engine in Logic Power v10, private PR #53, fixed at commit `ba10d0edc7eb20d499d0481fda2537e782b6efb2`.

## First compiled gate: capacity-expansion authorization

The candidate capacity expansion is authorized only when all three statements hold:

- the candidate station is genuinely capacity constrained;
- excess rework is not the limiting mechanism;
- supplier instability is not the limiting mechanism.

The finite model contains eight worlds from the three binary mechanisms. It exposes three admissible probes:

| Probe | Exact cost | Observation |
|---|---:|---|
| `first_pass_yield_audit` | 1 | rework excess or first-pass yield acceptable |
| `supplier_continuity_trace` | 1 | supplier unstable or stable |
| `capacity_stress_pilot` | 4 | capacity constrained or adequate |

The expensive stress pilot is run only after the two cheaper mechanisms fail to invalidate the intervention.

## Verified synthetic result

- hypotheses: 8;
- opposite-decision pairs: 7;
- minimum fixed probe set: all three probes;
- fixed cost: 6;
- optimal adaptive worst cost: 6;
- optimal adaptive expected cost: `5/2`;
- expected cost reduction versus the fixed panel: `7/12`, approximately 58.33%;
- optimal root probe: `first_pass_yield_audit`;
- altered certificate: rejected by both Python semantic replay and the independent Node/BigInt verifier.

Removing `supplier_continuity_trace` produces the exact obstruction:

```text
c1_q0_s0  versus  c1_q0_s1
```

Both worlds appear capacity constrained with acceptable quality. One authorizes capital expansion and the other forbids it because supplier instability is the real limiting mechanism. Without supplier evidence, the correct output is `IMPOSSIBLE`, not a guess.

## Reproduction

```bash
python -m unittest \
  logic_power_v10.test_logic_power_v10 \
  logistics_power_v1.test_logistics_power_v1
python -m logistics_power_v1.run_logistics_power_v1
python -m logic_power_v10.verify_logic_power_v10 \
  certificates/logistics_power_v1_capex_exact.json
python -m logic_power_v10.verify_logic_power_v10 \
  certificates/logistics_power_v1_capex_impossible.json
node logic_power_v10/verify_logic_power_v10.js \
  certificates/logistics_power_v1_capex_exact.json
node logic_power_v10/verify_logic_power_v10.js \
  certificates/logistics_power_v1_capex_impossible.json
# Both verifiers must reject the tampered negative control.
```

## Boundary

This closes a finite synthetic compiler gate. It does not prove that a real station is capacity constrained, that the probes are causally valid, or that an intervention is production-ready. Real promotion requires versioned event data, predeclared thresholds, a controlled pilot, service/cost/risk guardrails, and a reproducible before/after receipt.
