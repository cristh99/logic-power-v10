# Finance Logic v10 — Proof-Carrying Financial Decisions

This package applies the canonical Logic Power v10 active-discovery engine to finite financial decisions. It compiles each decision into hypotheses, admissible due-diligence experiments, an exact minimum fixed basis, an optimal adaptive policy and a deterministic SHA-256 certificate.

## Verified suite

- 5 exact financial decision cases;
- 1 exact impossibility/obstruction case;
- 160 finite hypotheses;
- 1,242 property-conflicting pairs;
- 6 proof-carrying certificates;
- 10/10 local tests passing.

| Case | Positive / negative worlds | Fixed cost | Adaptive expected cost | Reduction | Optimal first experiment |
|---|---:|---:|---:|---:|---|
| Capital allocation | 11 / 21 | 10 | `25/4 = 6.25` | `3/8 = 37.5%` | Signed customer contracts |
| Credit underwriting | 14 / 18 | 9 | `23/4 = 5.75` | `13/36 ≈ 36.11%` | Cash-flow quality audit |
| Liquidity survival | 14 / 18 | 7 | `35/8 = 4.375` | `3/8 = 37.5%` | Committed revolver confirmation |
| Portfolio mandate | 14 / 18 | 10 | `115/16 = 7.1875` | `9/32 = 28.125%` | Forward-return assumption audit |
| Bank stress resilience | 15 / 17 | 9 | `13/2 = 6.5` | `5/18 ≈ 27.78%` | Deposit concentration/runoff study |

Every axis in every exact case is materially necessary: omitting its sole separating experiment leaves at least one opposite-decision pair unresolved.

## Exact cases

### Capital allocation

Enumerates 32 worlds across contracted demand, capex certainty, funding cost, working-capital stress and terminal reinvestment discipline. A world is approved only when exact rational NPV is positive and liquidity headroom remains at least 100 units.

### Credit underwriting

Compiles cash-flow resilience, leverage, collateral recovery, customer concentration and covenant protection into a declared finite underwriting policy. The engine chooses the cheapest exact diligence sequence rather than collecting every item up front.

### Liquidity survival

Tests 90-day resilience across collections, inventory liquidation, revolver availability, maturity concentration and covenant headroom.

### Portfolio mandate

Tests whether a portfolio mandate is admissible across expected return, tail risk, redemption liquidity, look-through concentration and asset-liability matching.

### Bank stress resilience

Tests credit losses, deposit runoff, market losses, regulatory capital and unencumbered liquidity as one joint finite stress decision.

## Hidden-liability obstruction

A clean balance sheet and a hidden tax claim produce opposite decisions but remain observationally identical under the declared financial experiments. The engine returns `IMPOSSIBLE` with the exact witness pair instead of fabricating certainty. The remedy is to extend the experiment grammar with legal/tax-claim diligence.

## Reproduce

```bash
python3 -m unittest finance_logic_v10.test_finance_logic_v10
python3 -m finance_logic_v10.run_finance_logic_v10

for certificate in certificates/finance_*.json; do
  python3 logic_power_v10/verify_logic_power_v10.py "$certificate"
  node logic_power_v10/verify_logic_power_v10.js "$certificate"
done
```

## Boundary

The casebook is synthetic, finite, deterministic and exact-rational. Its charges, thresholds and priors are declared model inputs, not empirical estimates. It is a verified financial reasoning substrate—not financial advice, a complete valuation or risk platform, external SOTA evidence or a claim that the finance area has reached 1000/1000. Promotion requires real-data provenance, temporal validation, model-risk controls, legal applicability and independent replication.
