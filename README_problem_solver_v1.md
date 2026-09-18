# Logic Power Problem Solver v1 — Slice 2

This branch starts the general problem-solving layer without turning Logic into a monolith.

## Boundary

Logic remains the semantic and epistemic controller: representation, consequence, ambiguity, information acquisition, proof, obstruction, and certificate obligations.

Decision theory, planning/control, game theory, Monte Carlo/MCTS, learned planning, and domain sciences are registered solver capabilities. The router selects the smallest eligible primary method and records why other methods were rejected.

## Implemented

- immutable typed `ProblemIR` with deterministic canonical JSON and SHA-256 fingerprint;
- typed conditions, horizons, uncertainty models, model status, search budgets, and terminal states;
- rejection of mutable or non-canonical metadata;
- cross-runtime exact-number boundary: raw floats are prohibited and unsafe integers must be encoded as decimal strings;
- deterministic hybrid-problem classification;
- declarative solver registry for exact logic, Bayesian decision, robust regret, dynamic programming, zero-sum games, Monte Carlo, MCTS, and MuZero;
- fail-closed scope gates that prevent one-shot decision solvers or `logic_exact` from masquerading as sequential planners;
- Monte Carlo remains a supporting estimator and cannot be selected as a primary planner;
- exact-kernel gate for static two-agent, two-action zero-sum games;
- exact finite expected utility, minimax regret, and value of perfect information;
- exact pure or mixed equilibrium for 2x2 zero-sum games;
- seeded bounded Monte Carlo mean with a Hoeffding radius;
- exact finite-horizon MDP planning by backward dynamic programming with rational probabilities, rewards, discount, values, and deterministic tie-breaking;
- seeded UCT MCTS for one-agent deterministic simulators, with exact sampled-return accumulation and explicit rejection of nondeterministic simulators;
- MCTS promotion gate against an exact dynamic-programming oracle;
- fail-closed MuZero eligibility gate with positive rollout and depth budgets;
- deterministic terminal certificates;
- aligned Python and independent Node fingerprint and numeric validation;
- deterministic demo cases: decision `SOLVED`, game `SOLVED`, exact planning `SOLVED`, MCTS `SOLVED`, and MuZero gate `BLOCKED`.

## Planning benchmark

The exact two-step oracle evaluates:

```text
safe                 -> 4
explore -> good      -> 10
explore -> bad       -> -10
```

Exact dynamic programming selects `explore` with value `10`.

Seeded MCTS uses 500 rollouts, depth 2, and seed 17:

- selected action: `explore`;
- oracle match: true;
- visits: `explore=488`, `safe=12`;
- exact sampled mean: `explore=1215/122`, `safe=4`.

This verifies the small deterministic-simulator kernel. It is not a claim about stochastic chance-node MCTS, adversarial game-tree search, or large environments.

## MuZero rule

MuZero is only eligible when the problem declares a sequential single-agent task, learnable unknown dynamics, interaction data, a reward signal, neural training capability, and positive tree-search rollout and depth budgets. Eligibility is not a claim that MuZero is best: promotion still requires a sealed comparison against exact methods, dynamic programming, ordinary MCTS, and simpler baselines.

## Verification

```bash
bash logic_power_problem_solver_v1/ci_v1.sh
```

Current branch-equivalent isolated verification:

- 32 branch tests: PASS;
- Python compilation: PASS;
- five canonical certificates accepted by Node;
- tampered, non-hex, float, unsafe-integer, invalid-transition-mass, nondeterministic-simulator, Monte-Carlo-as-planner, and multi-agent-MCTS controls rejected;
- deterministic report and certificate rebuild: PASS.

The private GitHub Actions job does not currently obtain a runner or checkout step, so remote CI success is not claimed.

## Not yet implemented

- natural-language condition compiler;
- direct adapters to canonical Logic Power v10 and Power Compiler v6;
- POMDP and general partially observed planning;
- stochastic chance-node MCTS;
- adversarial extensive-form game-tree search;
- a learned MuZero implementation;
- TLA+ orchestration model;
- Lean boundary proofs;
- MotherDuck trace ledger and cross-domain benchmark matrix.

This is a hardened vertical slice, not completion of issue #82.
