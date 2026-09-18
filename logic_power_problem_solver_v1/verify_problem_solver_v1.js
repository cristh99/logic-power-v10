#!/usr/bin/env node
"use strict";

const crypto = require("node:crypto");
const fs = require("node:fs");

const SCHEMA = "logic-power-problem-solver/certificate/1";

function validateExactJson(value, path = "payload") {
  if (
    value === null ||
    typeof value === "string" ||
    typeof value === "boolean"
  ) {
    return [];
  }
  if (typeof value === "number") {
    return Number.isSafeInteger(value)
      ? []
      : [`${path}:noncanonical-number`];
  }
  if (Array.isArray(value)) {
    return value.flatMap((item, index) =>
      validateExactJson(item, `${path}[${index}]`),
    );
  }
  if (typeof value === "object") {
    return Object.keys(value).flatMap((key) =>
      validateExactJson(value[key], `${path}.${key}`),
    );
  }
  return [`${path}:unsupported-type`];
}

function canonical(value) {
  if (Array.isArray(value)) {
    return `[${value.map(canonical).join(",")}]`;
  }
  if (value !== null && typeof value === "object") {
    const keys = Object.keys(value).sort();
    return `{${keys
      .map((key) => `${JSON.stringify(key)}:${canonical(value[key])}`)
      .join(",")}}`;
  }
  return JSON.stringify(value);
}

function digest(value) {
  return crypto
    .createHash("sha256")
    .update(canonical(value), "utf8")
    .digest("hex");
}

function verify(certificate) {
  const errors = [];
  if (certificate.schema !== SCHEMA) errors.push("schema");
  if (
    !certificate.payload ||
    typeof certificate.payload !== "object" ||
    Array.isArray(certificate.payload)
  ) {
    errors.push("payload");
    return errors;
  }
  const canonicalErrors = validateExactJson(certificate.payload);
  if (canonicalErrors.length > 0) {
    errors.push("payload-canonical-json");
  }
  if (certificate.payload_sha256 !== digest(certificate.payload)) {
    errors.push("payload-hash");
  }
  const allowed = new Set([
    "SOLVED",
    "IMPOSSIBLE",
    "BLOCKED",
    "UNDERSPECIFIED",
    "BUDGET_EXHAUSTED",
    "UNSAFE",
  ]);
  if (!allowed.has(certificate.payload.status)) errors.push("status");
  for (const key of ["problem_fingerprint", "routing_fingerprint"]) {
    const value = certificate.payload[key];
    if (typeof value !== "string" || !/^[0-9a-f]{64}$/.test(value)) {
      errors.push(key);
    }
  }
  return errors;
}

if (process.argv.length !== 3) {
  console.error(
    "usage: verify_problem_solver_v1.js <certificate.json>",
  );
  process.exit(2);
}

let certificate;
try {
  certificate = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
} catch (error) {
  console.error(
    JSON.stringify({
      valid: false,
      errors: ["json"],
      detail: String(error),
    }),
  );
  process.exit(1);
}

const errors = verify(certificate);
console.log(JSON.stringify({ valid: errors.length === 0, errors }));
process.exit(errors.length === 0 ? 0 : 1);
