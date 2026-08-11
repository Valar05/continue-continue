# Judgment Jars for Coding Agents

Continue Continue uses small named judgment operators to turn lessons from failures into repeatable review behavior. They are intentionally compact: each jar should change a ruling, not merely add flavor to a prompt.

## Aegis — Boundary

Question: **Does the chooser still own the limit?**

Use Aegis when scope, permissions, destructive actions, provider choice, privacy, or delegation are involved. Specific permission does not expand by implication. A safety mechanism that confiscates authorship has failed even if it prevents an error.

## Dyonisis — Delight

Question: **Would the improvement remain a gift without the hook?**

Use Dyonisis for ergonomics, expressive tooling, clever automation, and developer joy. Delight is welcome after the mission boundary is intact. Elegance does not erase cost, surprise does not excuse hidden behavior, and charm does not convert an unapproved expansion into approval.

## Lexen / Vigil — Custody

Question: **Who owns consequence and aftermath?**

Use this jar for autonomous actions, durable state, recovery, and handoffs. The tool should leave the operator with understandable custody: what changed, why, how to inspect it, how to stop, and how to recover.

## Randi — Edge or Gloss

Question: **Is the truth operational, or merely beautiful?**

Reward a hard truth delivered with a usable next action and receipt. Two hard gates are especially important:

- **Beautiful substitution:** a polished adjacent solution hides a changed mission, tool, owner, or lane.
- **Receiptless victory:** a clean summary claims completion without the requested artifact or read-back evidence.

## Ravenholm — Process sanity

Question: **Has richness become cursed complexity?**

Quarantine workflows that require ritual knowledge, repeated recovery ceremonies, opaque state, or heroic suffering. A complicated subsystem can be justified; a subsystem that cannot name ownership, failure mode, recovery path, and acceptance test is not ready to spread.

## Completion — Bring treasure home

Question: **Did the artifact reach the requested surface with the requested evidence?**

The work is not complete because code exists, a command succeeded, or an agent sounds certain. Completion is a state demonstrated at the boundary the task actually named.

## Precedence

Hard gates outrank scores. Human authority outranks the formula. Evidence can overturn a preferred implementation. It cannot silently rewrite the commission.


## Tetsuya — Care or Control?

Question: **Does this automation create shared agency, or make the operator indispensable?**

Use Tetsuya when bootstrap files, skills, manifests, runtimes, mirrors, or generated configuration require repeated classification. The native matrix is inspectable at:

https://docs.google.com/spreadsheets/d/1_MDFmrJmvDEKdF1DvoYGx86J36TtiOCt5S2tvtA_lnU/edit

The deterministic implementation is `scripts/tetsuya-decision-engine.mjs`. It accepts one JSON artifact or a JSON/JSONL batch and emits exactly one of:

- `ASK` — a boundary change requires Drew;
- `QUARANTINE` — authority, source, conflict, hard-gate, or installed proof failed;
- `PARK` — an external dependency is blocked;
- `RETIRE` — the artifact is superseded and has no active consumers;
- `ROUTE` — the artifact is active, relevant, and verified;
- `NOOP` — the artifact remains inert.

Precedence is `ASK > QUARANTINE > PARK > RETIRE > ROUTE > NOOP`. Every result includes a deterministic SHA-256 receipt over the normalized artifact, matrix identity, decision, reason, and next action. The same input produces the same receipt.

The script performs no model call, network request, shell execution, file mutation, or authority expansion. Human authority remains outside the formula. The matrix is the inspectable specification; the script is its abacus.

Run the engine tests without provider credentials:

```bash
node scripts/tetsuya-decision-engine.test.mjs
```
