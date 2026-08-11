import assert from "node:assert/strict";

import {
  MATRIX_VERSION,
  classifyArtifact,
  classifyArtifacts,
} from "./tetsuya-decision-engine.mjs";

const base = {
  artifact_id: "fixture",
  declared_status: "ACTIVE",
  source_verified: 1,
  installed_required: 0,
  installed_verified: 0,
  active_consumers: 1,
  conflicting_active_claims: 0,
  boundary_change: 0,
  blocked: 0,
  superseded: 0,
  trigger_match: 1,
  hard_gate: "",
};

assert.equal(classifyArtifact(base).decision, "ROUTE");
assert.equal(classifyArtifact({ ...base, trigger_match: 0 }).decision, "NOOP");
assert.equal(classifyArtifact({ ...base, superseded: 1, active_consumers: 0, trigger_match: 0 }).decision, "RETIRE");
assert.equal(classifyArtifact({ ...base, blocked: 1, trigger_match: 0 }).decision, "PARK");
assert.equal(classifyArtifact({ ...base, hard_gate: "source conflict", blocked: 1 }).decision, "QUARANTINE");
assert.equal(classifyArtifact({ ...base, boundary_change: 1, hard_gate: "also unsafe" }).decision, "ASK");
assert.equal(classifyArtifact({ ...base, installed_required: 1, installed_verified: 0 }).decision, "QUARANTINE");
assert.equal(classifyArtifact({ ...base, conflicting_active_claims: 1 }).decision, "QUARANTINE");

const first = classifyArtifact(base);
const second = classifyArtifact({ ...base });
assert.equal(first.receipt_sha256, second.receipt_sha256, "same input must produce the same receipt");
assert.equal(first.matrix_version, MATRIX_VERSION);
assert.equal(first.human_authority_outside_formula, true);

const batch = classifyArtifacts([
  base,
  { ...base, artifact_id: "blocked", blocked: 1, trigger_match: 0 },
  { ...base, artifact_id: "unsafe", source_verified: 0 },
]);
assert.equal(batch.results.length, 3);
assert.equal(batch.exit_code, 5);
assert.match(batch.batch_sha256, /^[a-f0-9]{64}$/);

assert.throws(() => classifyArtifact({ ...base, artifact_id: "" }), /artifact_id is required/);
assert.throws(() => classifyArtifact({ ...base, active_consumers: -1 }), /non-negative integer/);
assert.throws(() => classifyArtifacts({}), /batch input must be an array/);

console.log("Tetsuya decision engine tests passed: 15 assertions.");
