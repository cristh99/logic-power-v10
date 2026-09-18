#!/usr/bin/env node
"use strict";

const fs = require("fs");
const crypto = require("crypto");

function stableStringify(value) {
  if (value === null || typeof value !== "object") {
    return JSON.stringify(value);
  }
  if (Array.isArray(value)) {
    return `[${value.map(stableStringify).join(",")}]`;
  }
  const keys = Object.keys(value).sort();
  return `{${keys
    .map((key) => `${JSON.stringify(key)}:${stableStringify(value[key])}`)
    .join(",")}}`;
}

function gcd(a, b) {
  a = a < 0n ? -a : a;
  b = b < 0n ? -b : b;
  while (b !== 0n) [a, b] = [b, a % b];
  return a;
}

function rat(n, d = 1n) {
  if (d === 0n) throw new Error("zero denominator");
  if (d < 0n) {
    n = -n;
    d = -d;
  }
  const g = gcd(n, d);
  return [n / g, d / g];
}

function parseRat(value) {
  if (
    !Array.isArray(value) ||
    value.length !== 2 ||
    !Number.isInteger(value[0]) ||
    !Number.isInteger(value[1]) ||
    value[1] <= 0
  ) {
    throw new Error("invalid fraction");
  }
  return rat(BigInt(value[0]), BigInt(value[1]));
}

function add(a, b) {
  return rat(a[0] * b[1] + b[0] * a[1], a[1] * b[1]);
}
function mul(a, b) {
  return rat(a[0] * b[0], a[1] * b[1]);
}
function div(a, b) {
  return rat(a[0] * b[1], a[1] * b[0]);
}
function cmp(a, b) {
  const value = a[0] * b[1] - b[0] * a[1];
  return value < 0n ? -1 : value > 0n ? 1 : 0;
}
function eq(a, b) {
  return cmp(a, b) === 0;
}
function pairKey(a, b) {
  return a < b ? `${a}\u0000${b}` : `${b}\u0000${a}`;
}

function verify(certificate) {
  const errors = [];
  if (
    !certificate ||
    typeof certificate !== "object" ||
    !certificate.payload ||
    typeof certificate.sha256 !== "string"
  ) {
    return ["certificate-shape"];
  }

  const digest = crypto
    .createHash("sha256")
    .update(stableStringify(certificate.payload), "utf8")
    .digest("hex");
  if (digest !== certificate.sha256) return ["payload-hash"];

  const payload = certificate.payload;
  if (
    payload.schema !==
    "logic-power-v10/active-discovery-certificate/1"
  ) {
    errors.push("schema");
  }
  const problem = payload.problem;
  if (
    !problem ||
    !Array.isArray(problem.hypotheses) ||
    !Array.isArray(problem.experiments)
  ) {
    return ["problem-shape"];
  }

  const ids = problem.hypotheses.map((hypothesis) => hypothesis.id);
  if (ids.length === 0 || new Set(ids).size !== ids.length) {
    errors.push("hypotheses");
  }
  const property = new Map();
  const prior = new Map();
  for (const hypothesis of problem.hypotheses) {
    if (
      typeof hypothesis.id !== "string" ||
      typeof hypothesis.property !== "boolean"
    ) {
      errors.push("hypothesis-shape");
    }
    property.set(hypothesis.id, hypothesis.property);
    try {
      prior.set(hypothesis.id, parseRat(hypothesis.prior));
    } catch {
      errors.push("prior");
    }
  }
  let priorTotal = rat(0n);
  for (const id of ids) {
    priorTotal = add(priorTotal, prior.get(id));
  }
  if (!eq(priorTotal, rat(1n))) errors.push("prior-total");

  const experiments = new Map();
  for (const experiment of problem.experiments) {
    if (experiments.has(experiment.name)) {
      errors.push("experiment-duplicate");
    }
    let cost;
    try {
      cost = parseRat(experiment.cost);
    } catch {
      errors.push("experiment-cost");
      cost = rat(0n);
    }
    if (cmp(cost, rat(0n)) <= 0) {
      errors.push("experiment-cost-positive");
    }
    const observedIds = experiment.observations
      ? Object.keys(experiment.observations).sort()
      : [];
    if (observedIds.join("\u0000") !== [...ids].sort().join("\u0000")) {
      errors.push("experiment-observations");
    }
    experiments.set(experiment.name, {
      name: experiment.name,
      cost,
      observations: experiment.observations,
    });
  }
  const orderedExperiments = [...experiments.values()].sort((a, b) =>
    a.name.localeCompare(b.name)
  );

  const conflicts = [];
  for (let left = 0; left < ids.length; left += 1) {
    for (let right = left + 1; right < ids.length; right += 1) {
      if (property.get(ids[left]) !== property.get(ids[right])) {
        conflicts.push([ids[left], ids[right]].sort());
      }
    }
  }
  conflicts.sort((a, b) => pairKey(...a).localeCompare(pairKey(...b)));
  if (
    stableStringify(payload.analysis.conflict_pairs) !==
    stableStringify(conflicts)
  ) {
    errors.push("conflict-pairs");
  }

  const separates = (experiment, pair) =>
    experiment.observations[pair[0]] !==
    experiment.observations[pair[1]];

  function obstructionFor(belief) {
    const beliefSet = new Set(belief);
    for (const pair of conflicts) {
      if (
        beliefSet.has(pair[0]) &&
        beliefSet.has(pair[1]) &&
        !orderedExperiments.some((experiment) =>
          separates(experiment, pair)
        )
      ) {
        return pair;
      }
    }
    return null;
  }

  function minimumBasis() {
    if (conflicts.length === 0) {
      return { names: [], cost: rat(0n) };
    }
    if (obstructionFor(ids)) return null;
    let best = null;
    const limit = 1 << orderedExperiments.length;
    for (let mask = 1; mask < limit; mask += 1) {
      const selected = [];
      let cost = rat(0n);
      for (
        let index = 0;
        index < orderedExperiments.length;
        index += 1
      ) {
        if (mask & (1 << index)) {
          selected.push(orderedExperiments[index]);
          cost = add(cost, orderedExperiments[index].cost);
        }
      }
      if (
        !conflicts.every((pair) =>
          selected.some((experiment) => separates(experiment, pair))
        )
      ) {
        continue;
      }
      const candidate = {
        names: selected.map((experiment) => experiment.name),
        cost,
      };
      const candidateKey = candidate.names.join("\u0000");
      const bestKey = best ? best.names.join("\u0000") : "";
      if (
        !best ||
        cmp(candidate.cost, best.cost) < 0 ||
        (cmp(candidate.cost, best.cost) === 0 &&
          (candidate.names.length < best.names.length ||
            (candidate.names.length === best.names.length &&
              candidateKey < bestKey)))
      ) {
        best = candidate;
      }
    }
    return best;
  }

  const bestBasis = minimumBasis();
  const declaredBasis = payload.analysis.fixed_basis;
  if (bestBasis === null) {
    if (
      declaredBasis !== null ||
      payload.analysis.fixed_basis_cost !== null
    ) {
      errors.push("fixed-basis-impossible");
    }
  } else {
    if (
      stableStringify(declaredBasis) !==
      stableStringify(bestBasis.names)
    ) {
      errors.push("fixed-basis-optimum");
    }
    try {
      if (
        !eq(
          parseRat(payload.analysis.fixed_basis_cost),
          bestBasis.cost
        )
      ) {
        errors.push("fixed-basis-cost");
      }
    } catch {
      errors.push("fixed-basis-cost");
    }
  }

  const cegis = payload.analysis.cegis_basis;
  if (cegis === null) {
    if (obstructionFor(ids) === null) errors.push("cegis-null");
  } else {
    const selected = cegis.map((name) => experiments.get(name));
    if (
      selected.some((experiment) => !experiment) ||
      !conflicts.every((pair) =>
        selected.some((experiment) => separates(experiment, pair))
      )
    ) {
      errors.push("cegis-coverage");
    }
  }

  const declaredObstruction = payload.analysis.obstruction;
  const actualObstruction = obstructionFor(ids);
  if (
    stableStringify(declaredObstruction) !==
    stableStringify(actualObstruction)
  ) {
    errors.push("obstruction");
  }

  const memo = new Map();
  const mass = (belief) =>
    belief.reduce(
      (total, id) => add(total, prior.get(id)),
      rat(0n)
    );
  const status = (belief) => {
    if (belief.length === 0) return "INCONSISTENT";
    const values = new Set(
      belief.map((id) => property.get(id))
    );
    if (values.size === 1) {
      return values.has(true) ? "TRUE" : "FALSE";
    }
    return "UNKNOWN";
  };

  function optimal(belief) {
    const normalized = [...belief].sort();
    const key = normalized.join("\u0000");
    if (memo.has(key)) return memo.get(key);
    const currentStatus = status(normalized);
    if (
      currentStatus === "TRUE" ||
      currentStatus === "FALSE"
    ) {
      const terminal = {
        exact: true,
        worst: rat(0n),
        expected: rat(0n),
        experiment: null,
        status: currentStatus,
      };
      memo.set(key, terminal);
      return terminal;
    }

    const candidates = [];
    const totalMass = mass(normalized);
    for (const experiment of orderedExperiments) {
      const groups = new Map();
      for (const id of normalized) {
        const observation = experiment.observations[id];
        if (!groups.has(observation)) groups.set(observation, []);
        groups.get(observation).push(id);
      }
      if (groups.size <= 1) continue;
      let exact = true;
      let worstChild = rat(0n);
      let expected = experiment.cost;
      for (const child of groups.values()) {
        const solved = optimal(child);
        if (!solved.exact) {
          exact = false;
          break;
        }
        if (cmp(solved.worst, worstChild) > 0) {
          worstChild = solved.worst;
        }
        expected = add(
          expected,
          mul(div(mass(child), totalMass), solved.expected)
        );
      }
      if (!exact) continue;
      candidates.push({
        exact: true,
        worst: add(experiment.cost, worstChild),
        expected,
        experiment: experiment.name,
        status: "UNKNOWN",
      });
    }

    let result;
    if (candidates.length === 0) {
      result = {
        exact: false,
        worst: rat(0n),
        expected: rat(0n),
        experiment: null,
        status: "IMPOSSIBLE",
      };
    } else {
      candidates.sort(
        (a, b) =>
          cmp(a.worst, b.worst) ||
          cmp(a.expected, b.expected) ||
          a.experiment.localeCompare(b.experiment)
      );
      result = candidates[0];
    }
    memo.set(key, result);
    return result;
  }

  function verifyTree(node, expectedBelief) {
    const normalized = [...expectedBelief].sort();
    if (
      !node ||
      stableStringify(node.belief) !==
        stableStringify(normalized)
    ) {
      errors.push("tree-belief");
      return;
    }
    const optimum = optimal(normalized);
    if (node.status !== optimum.status) errors.push("tree-status");
    try {
      if (!eq(parseRat(node.worst_cost), optimum.worst)) {
        errors.push("tree-worst");
      }
      if (!eq(parseRat(node.expected_cost), optimum.expected)) {
        errors.push("tree-expected");
      }
    } catch {
      errors.push("tree-cost-shape");
    }

    if (
      optimum.status === "TRUE" ||
      optimum.status === "FALSE"
    ) {
      return;
    }
    if (optimum.status === "IMPOSSIBLE") {
      const obstruction = obstructionFor(normalized);
      if (
        !obstruction ||
        stableStringify(node.obstruction) !==
          stableStringify(obstruction)
      ) {
        errors.push("tree-obstruction");
      }
      return;
    }

    if (
      node.experiment !== optimum.experiment ||
      !experiments.has(node.experiment)
    ) {
      errors.push("tree-experiment");
      return;
    }
    const experiment = experiments.get(node.experiment);
    try {
      if (
        !eq(
          parseRat(node.experiment_cost),
          experiment.cost
        )
      ) {
        errors.push("tree-experiment-cost");
      }
    } catch {
      errors.push("tree-experiment-cost");
    }

    const groups = new Map();
    for (const id of normalized) {
      const observation = experiment.observations[id];
      if (!groups.has(observation)) groups.set(observation, []);
      groups.get(observation).push(id);
    }
    if (
      stableStringify(Object.keys(node.children).sort()) !==
      stableStringify([...groups.keys()].sort())
    ) {
      errors.push("tree-children");
      return;
    }
    for (const [observation, childBelief] of groups) {
      verifyTree(node.children[observation], childBelief);
    }
  }

  const policy = payload.analysis.policy;
  const rootOptimum = optimal(ids);
  if (policy.exact !== rootOptimum.exact) {
    errors.push("policy-exact");
  }
  try {
    if (!eq(parseRat(policy.worst_cost), rootOptimum.worst)) {
      errors.push("policy-worst");
    }
    if (!eq(parseRat(policy.expected_cost), rootOptimum.expected)) {
      errors.push("policy-expected");
    }
  } catch {
    errors.push("policy-cost-shape");
  }
  verifyTree(policy.tree, ids);

  return [...new Set(errors)];
}

function main() {
  if (process.argv.length !== 3) {
    console.error(
      "usage: verify_logic_power_v10.js CERTIFICATE.json"
    );
    process.exit(2);
  }
  let certificate;
  try {
    certificate = JSON.parse(
      fs.readFileSync(process.argv[2], "utf8")
    );
  } catch (error) {
    console.log(
      JSON.stringify({
        valid: false,
        errors: [`read:${error.name}`],
      })
    );
    process.exit(1);
  }
  const errors = verify(certificate);
  console.log(
    JSON.stringify({ valid: errors.length === 0, errors })
  );
  process.exit(errors.length === 0 ? 0 : 1);
}

main();
