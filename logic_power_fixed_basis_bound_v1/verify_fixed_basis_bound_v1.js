#!/usr/bin/env node
"use strict";

// Independent verifier for logic-power-v10/fixed-basis-bound-certificate/1.
// Shares no code with the Python producer or verifier: canonical JSON,
// rational arithmetic and every check are reimplemented here on BigInt.
// This verifier never enumerates subsets of experiments and never rebuilds
// the certificate: it checks that the declared basis separates every
// conflict pair and that the declared dual is feasible, which already
// proves the lower bound.

const fs = require("fs");
const crypto = require("crypto");

const SCHEMA = "logic-power-v10/fixed-basis-bound-certificate/1";

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

function addRat(a, b) {
  return rat(a[0] * b[1] + b[0] * a[1], a[1] * b[1]);
}

function cmpRat(a, b) {
  const value = a[0] * b[1] - b[0] * a[1];
  return value < 0n ? -1 : value > 0n ? 1 : 0;
}

function eqRat(a, b) {
  return cmpRat(a, b) === 0;
}

function strCmp(a, b) {
  return a < b ? -1 : a > b ? 1 : 0;
}

function pairCmp(p, q) {
  return strCmp(p[0], q[0]) || strCmp(p[1], q[1]);
}

function isPair(value) {
  return (
    Array.isArray(value) &&
    value.length === 2 &&
    typeof value[0] === "string" &&
    typeof value[1] === "string"
  );
}

function parseProblem(problem) {
  if (
    !problem ||
    typeof problem !== "object" ||
    !Array.isArray(problem.hypotheses) ||
    !Array.isArray(problem.experiments)
  ) {
    return null;
  }
  const property = new Map();
  for (const hypothesis of problem.hypotheses) {
    if (
      !hypothesis ||
      typeof hypothesis !== "object" ||
      typeof hypothesis.id !== "string" ||
      !("property" in hypothesis) ||
      !("prior" in hypothesis)
    ) {
      return null;
    }
    let prior;
    try {
      prior = parseRat(hypothesis.prior);
    } catch {
      return null;
    }
    if (cmpRat(prior, rat(0n)) <= 0) return null;
    property.set(hypothesis.id, Boolean(hypothesis.property));
  }
  const ids = [...property.keys()];
  if (ids.length === 0 || new Set(ids).size !== ids.length) return null;
  const sortedIds = [...ids].sort(strCmp);

  const experiments = new Map();
  for (const experiment of problem.experiments) {
    if (
      !experiment ||
      typeof experiment !== "object" ||
      typeof experiment.name !== "string" ||
      experiment.name.length === 0 ||
      experiments.has(experiment.name)
    ) {
      return null;
    }
    let cost;
    try {
      cost = parseRat(experiment.cost);
    } catch {
      return null;
    }
    if (cmpRat(cost, rat(0n)) <= 0) return null;
    const observations = experiment.observations;
    if (
      !observations ||
      typeof observations !== "object" ||
      Array.isArray(observations)
    ) {
      return null;
    }
    const observed = Object.keys(observations).sort(strCmp);
    if (observed.join("") !== sortedIds.join("")) return null;
    experiments.set(experiment.name, { name: experiment.name, cost, observations });
  }
  const ordered = [...experiments.values()].sort((a, b) =>
    strCmp(a.name, b.name)
  );
  return { ids: sortedIds, property, experiments: ordered };
}

function verify(certificate) {
  if (
    !certificate ||
    typeof certificate !== "object" ||
    Array.isArray(certificate) ||
    !certificate.payload ||
    typeof certificate.payload !== "object" ||
    Array.isArray(certificate.payload) ||
    typeof certificate.sha256 !== "string"
  ) {
    return ["certificate-shape"];
  }
  const digest = crypto
    .createHash("sha256")
    .update(stableStringify(certificate.payload), "utf8")
    .digest("hex");
  if (digest !== certificate.sha256) return ["payload-hash"];

  const errors = [];
  const payload = certificate.payload;
  if (payload.schema !== SCHEMA) errors.push("schema");

  const parsed = parseProblem(payload.problem);
  if (parsed === null) return errors.concat(["problem-shape"]);
  const { ids, property, experiments } = parsed;
  const experimentCosts = new Map(
    experiments.map((experiment) => [experiment.name, experiment.cost])
  );

  const conflicts = [];
  for (let left = 0; left < ids.length; left += 1) {
    for (let right = left + 1; right < ids.length; right += 1) {
      if (property.get(ids[left]) !== property.get(ids[right])) {
        conflicts.push([ids[left], ids[right]]);
      }
    }
  }
  const conflictKeys = new Set(
    conflicts.map((pair) => stableStringify(pair))
  );
  const separates = (experiment, pair) =>
    experiment.observations[pair[0]] !== experiment.observations[pair[1]];
  const separatorsOf = (pair) =>
    experiments.filter((experiment) => separates(experiment, pair));

  let actualObstruction = null;
  for (const pair of conflicts) {
    if (separatorsOf(pair).length === 0) {
      actualObstruction = pair;
      break;
    }
  }

  const analysis =
    payload.analysis && typeof payload.analysis === "object"
      ? payload.analysis
      : {};

  if (
    stableStringify(analysis.obstruction === undefined ? null : analysis.obstruction) !==
    stableStringify(actualObstruction)
  ) {
    errors.push("obstruction");
  }

  if (actualObstruction !== null) {
    const fields = [
      "fixed_basis",
      "fixed_basis_cost",
      "forced_experiments",
      "dual",
      "tight",
    ];
    if (fields.some((field) => analysis[field] !== null && analysis[field] !== undefined)) {
      errors.push("impossible-shape");
    }
    return [...new Set(errors)];
  }

  const declaredBasis = analysis.fixed_basis;
  let basisNames = [];
  if (
    !Array.isArray(declaredBasis) ||
    declaredBasis.some((name) => typeof name !== "string") ||
    new Set(declaredBasis).size !== declaredBasis.length ||
    declaredBasis.some((name) => !experimentCosts.has(name))
  ) {
    errors.push("basis-cover");
  } else {
    basisNames = [...declaredBasis];
    const chosen = experiments.filter((experiment) =>
      basisNames.includes(experiment.name)
    );
    if (
      conflicts.some(
        (pair) => !chosen.some((experiment) => separates(experiment, pair))
      )
    ) {
      errors.push("basis-cover");
    }
  }

  let declaredCost = null;
  try {
    declaredCost = parseRat(analysis.fixed_basis_cost);
  } catch {
    errors.push("basis-cost");
  }
  if (declaredCost !== null) {
    const actual = basisNames.reduce(
      (total, name) => addRat(total, experimentCosts.get(name)),
      rat(0n)
    );
    if (!eqRat(declaredCost, actual)) errors.push("basis-cost");
  }

  const declaredForced = analysis.forced_experiments;
  const forcedMap = new Map();
  for (const pair of conflicts) {
    const separators = separatorsOf(pair);
    if (separators.length === 1) {
      const name = separators[0].name;
      if (!forcedMap.has(name) || pairCmp(pair, forcedMap.get(name)) < 0) {
        forcedMap.set(name, pair);
      }
    }
  }
  const expectedForced = [...forcedMap.entries()]
    .sort((a, b) => strCmp(a[0], b[0]))
    .map(([name, pair]) => ({
      experiment: name,
      witness_pair: [pair[0], pair[1]],
    }));
  const forcedWellFormed =
    Array.isArray(declaredForced) &&
    declaredForced.every(
      (entry) =>
        entry &&
        typeof entry === "object" &&
        typeof entry.experiment === "string" &&
        isPair(entry.witness_pair)
    );
  if (
    stableStringify(
      declaredForced === undefined ? null : declaredForced
    ) !== stableStringify(expectedForced)
  ) {
    errors.push("forced-experiments");
  }
  if (
    forcedWellFormed &&
    declaredForced.some((entry) => !basisNames.includes(entry.experiment))
  ) {
    errors.push("forced-subset");
  }

  let dualWeights = [];
  let dualValue = null;
  const dual = analysis.dual;
  let dualMalformed =
    !dual ||
    typeof dual !== "object" ||
    Array.isArray(dual) ||
    !Array.isArray(dual.weights);
  if (!dualMalformed) {
    let previous = null;
    for (const entry of dual.weights) {
      if (
        !Array.isArray(entry) ||
        entry.length !== 2 ||
        !isPair(entry[0]) ||
        entry[0][0] >= entry[0][1] ||
        !conflictKeys.has(stableStringify(entry[0])) ||
        (previous !== null && pairCmp(entry[0], previous) <= 0)
      ) {
        dualMalformed = true;
        break;
      }
      previous = entry[0];
      let weight;
      try {
        weight = parseRat(entry[1]);
      } catch {
        dualMalformed = true;
        break;
      }
      if (cmpRat(weight, rat(0n)) <= 0) {
        dualMalformed = true;
        break;
      }
      dualWeights.push({ pair: entry[0], weight });
    }
    if (!dualMalformed) {
      try {
        dualValue = parseRat(dual.value);
      } catch {
        dualMalformed = true;
      }
    }
  }
  if (dualMalformed) {
    errors.push("dual-shape");
  } else {
    for (const experiment of experiments) {
      const load = dualWeights.reduce(
        (total, entry) =>
          separates(experiment, entry.pair)
            ? addRat(total, entry.weight)
            : total,
        rat(0n)
      );
      if (cmpRat(load, experiment.cost) > 0) {
        errors.push("dual-feasible");
        break;
      }
    }
    const total = dualWeights.reduce(
      (sumRat, entry) => addRat(sumRat, entry.weight),
      rat(0n)
    );
    if (!eqRat(dualValue, total)) errors.push("dual-value");
    if (declaredCost !== null && cmpRat(dualValue, declaredCost) > 0) {
      errors.push("dual-bound");
    }
  }

  const expectedTight =
    dualValue !== null &&
    declaredCost !== null &&
    eqRat(dualValue, declaredCost);
  if (
    typeof analysis.tight !== "boolean" ||
    analysis.tight !== expectedTight
  ) {
    errors.push("tight-flag");
  }

  return [...new Set(errors)];
}

function main() {
  if (process.argv.length !== 3) {
    console.error(
      "usage: verify_fixed_basis_bound_v1.js CERTIFICATE.json"
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
        errors: [`read:${error.name}`],
        valid: false,
      })
    );
    process.exit(1);
  }
  const errors = verify(certificate);
  console.log(
    JSON.stringify({ errors, valid: errors.length === 0 })
  );
  process.exit(errors.length === 0 ? 0 : 1);
}

main();
