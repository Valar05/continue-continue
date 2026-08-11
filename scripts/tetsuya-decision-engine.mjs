#!/usr/bin/env node

import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { pathToFileURL } from "node:url";

export const MATRIX_VERSION = "tetsuya.bootstrap.matrix.v1";
export const MATRIX_SHEET_ID = "1_MDFmrJmvDEKdF1DvoYGx86J36TtiOCt5S2tvtA_lnU";

const DECISIONS = Object.freeze({
  ASK: {
    reason: "Boundary change requires Drew.",
    next_action: "Stop and emit the smallest explicit human-authority question.",
    exit_code: 4,
  },
  QUARANTINE: {
    reason: "Authority, source, conflict, or installed proof failed.",
    next_action: "Exclude from execution, preserve evidence, and repair the named proof.",
    exit_code: 5,
  },
  PARK: {
    reason: "A required dependency is blocked.",
    next_action: "Preserve the exact blocker and resume the same lane when it clears.",
    exit_code: 3,
  },
  RETIRE: {
    reason: "The artifact is superseded and has no active consumers.",
    next_action: "Remove active routing while retaining lineage and a successor pointer.",
    exit_code: 0,
  },
  ROUTE: {
    reason: "The artifact is active, relevant, and verified.",
    next_action: "Load it for the bounded case and record the receipt.",
    exit_code: 0,
  },
  NOOP: {
    reason: "No higher-precedence rule matched.",
    next_action: "Keep the artifact inert; existence alone does not justify loading it.",
    exit_code: 0,
  },
});

function canonical(value) {
  if (Array.isArray(value)) return value.map(canonical);
  if (value && typeof value === "object") {
    return Object.fromEntries(
      Object.keys(value)
        .sort()
        .map((key) => [key, canonical(value[key])]),
    );
  }
  return value;
}

function sha256(value) {
  return createHash("sha256")
    .update(JSON.stringify(canonical(value)))
    .digest("hex");
}

function flag(value, field) {
  if (value === true || value === 1 || value === "1") return true;
  if (value === false || value === 0 || value === "0" || value === "" || value == null) return false;
  throw new TypeError(`${field} must be boolean-like`);
}

function count(value, field) {
  const parsed = Number(value ?? 0);
  if (!Number.isInteger(parsed) || parsed < 0) throw new TypeError(`${field} must be a non-negative integer`);
  return parsed;
}

export function normalizeArtifact(input) {
  if (!input || typeof input !== "object" || Array.isArray(input)) throw new TypeError("artifact must be an object");
  const artifact_id = String(input.artifact_id ?? "").trim();
  const declared_status = String(input.declared_status ?? "").trim().toUpperCase();
  if (!artifact_id) throw new TypeError("artifact_id is required");
  if (!declared_status) throw new TypeError("declared_status is required");

  return {
    artifact_id,
    name: String(input.name ?? artifact_id).trim(),
    kind: String(input.kind ?? "unknown").trim(),
    scope: String(input.scope ?? "unknown").trim(),
    declared_status,
    source_verified: flag(input.source_verified, "source_verified"),
    installed_required: flag(input.installed_required, "installed_required"),
    installed_verified: flag(input.installed_verified, "installed_verified"),
    active_consumers: count(input.active_consumers, "active_consumers"),
    conflicting_active_claims: count(input.conflicting_active_claims, "conflicting_active_claims"),
    boundary_change: flag(input.boundary_change, "boundary_change"),
    blocked: flag(input.blocked, "blocked"),
    superseded: flag(input.superseded, "superseded"),
    trigger_match: flag(input.trigger_match, "trigger_match"),
    hard_gate: String(input.hard_gate ?? "").trim(),
  };
}

function chooseDecision(artifact) {
  if (artifact.boundary_change) return "ASK";
  if (
    artifact.hard_gate ||
    !artifact.source_verified ||
    artifact.conflicting_active_claims > 0 ||
    (artifact.installed_required && !artifact.installed_verified)
  ) return "QUARANTINE";
  if (artifact.blocked) return "PARK";
  if (artifact.superseded && artifact.active_consumers === 0) return "RETIRE";
  if (artifact.trigger_match && artifact.declared_status === "ACTIVE") return "ROUTE";
  return "NOOP";
}

export function classifyArtifact(input) {
  const artifact = normalizeArtifact(input);
  const decision = chooseDecision(artifact);
  const policy = DECISIONS[decision];
  const receiptMaterial = {
    schema: "tetsuya.decision-receipt.v1",
    matrix_version: MATRIX_VERSION,
    matrix_sheet_id: MATRIX_SHEET_ID,
    governor: "Tetsuya — Care or Control?",
    artifact,
    decision,
    reason: policy.reason,
    next_action: policy.next_action,
    human_authority_outside_formula: true,
  };
  return {
    ...receiptMaterial,
    receipt_sha256: sha256(receiptMaterial),
    exit_code: policy.exit_code,
  };
}

export function classifyArtifacts(inputs) {
  if (!Array.isArray(inputs)) throw new TypeError("batch input must be an array");
  const results = inputs.map(classifyArtifact);
  return {
    schema: "tetsuya.decision-batch.v1",
    matrix_version: MATRIX_VERSION,
    results,
    exit_code: Math.max(0, ...results.map((result) => result.exit_code)),
    batch_sha256: sha256(results.map(({ receipt_sha256 }) => receipt_sha256)),
  };
}

function parseInput(text) {
  const trimmed = text.trim();
  if (!trimmed) throw new TypeError("input is empty");
  try {
    return JSON.parse(trimmed);
  } catch {
    return trimmed.split(/\r?\n/).filter(Boolean).map((line) => JSON.parse(line));
  }
}

function main(argv) {
  const inputIndex = argv.indexOf("--input");
  if (inputIndex < 0 || !argv[inputIndex + 1]) {
    console.error("usage: tetsuya-decision-engine.mjs --input <json-or-jsonl-file>");
    return 2;
  }
  try {
    const value = parseInput(readFileSync(argv[inputIndex + 1], "utf8"));
    const output = Array.isArray(value) ? classifyArtifacts(value) : classifyArtifact(value);
    process.stdout.write(`${JSON.stringify(output, null, 2)}\n`);
    return output.exit_code;
  } catch (error) {
    console.error(JSON.stringify({ schema: "tetsuya.decision-error.v1", error: error.message }));
    return 2;
  }
}

if (import.meta.url === pathToFileURL(process.argv[1]).href) process.exitCode = main(process.argv.slice(2));

