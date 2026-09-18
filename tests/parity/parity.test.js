"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const crypto = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");
const { spawnSync } = require("node:child_process");

const PARITY = __dirname;
const ROOT = path.join(PARITY, "..", "..");
const VERIFIER = path.join(
  ROOT,
  "logic_power_v10",
  "verify_logic_power_v10.js"
);
const { stableStringify } = require(VERIFIER);

const fixture = JSON.parse(
  fs.readFileSync(path.join(PARITY, "canonical_cases.json"), "utf8")
);
const divergences = fixture.known_divergences || {};

function sha256Hex(text) {
  return crypto.createHash("sha256").update(text, "utf8").digest("hex");
}

test("fixture is well formed", () => {
  const names = fixture.cases.map((testCase) => testCase.name);
  assert.equal(new Set(names).size, names.length);
  for (const name of Object.keys(divergences)) {
    assert.ok(names.includes(name), `unknown divergence ${name}`);
  }
});

for (const testCase of fixture.cases) {
  test(`canonical bytes: ${testCase.name}`, () => {
    const divergence = divergences[testCase.name];
    if (divergence) {
      assert.equal(
        stableStringify(testCase.value),
        divergence.node_canonical
      );
      assert.equal(
        sha256Hex(divergence.node_canonical),
        divergence.node_sha256
      );
      assert.ok(divergence.reason);
    } else {
      assert.equal(stableStringify(testCase.value), testCase.canonical);
      assert.equal(sha256Hex(testCase.canonical), testCase.sha256);
    }
  });
}

test("tampered certificate rejected", () => {
  const completed = spawnSync(
    process.execPath,
    [VERIFIER, path.join(PARITY, "logic_power_v10_exact_tampered.json")],
    { encoding: "utf8" }
  );
  assert.equal(completed.status, 1);
  assert.deepEqual(JSON.parse(completed.stdout), {
    valid: false,
    errors: ["payload-hash"],
  });
});
