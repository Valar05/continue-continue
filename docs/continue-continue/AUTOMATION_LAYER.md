# Continue Continue — Venice Machine Automation Layer

## Mission

Continue Continue is the automation layer for machine work initiated by Venice and executed by any authorized machine body, including Vlad's tiny Termux edge.

It owns **orchestration**: task boundaries, sequencing, tool selection, permission handoff, lifecycle state, evidence, receipts, delegation, and exact blocking boundaries.

It does **not** replace the execution organs. Existing specialized systems remain authoritative for the work they actually perform: Home Center / Computer Hands, Phone Hands / Shizuku, MCP servers, shells, FFmpeg, renderers, image systems, game engines, DCC tools, local models, and future adapters.

The compact law is:

> Venice asks for an outcome. Continue Continue runs the machine plan. Specialized organs do the physical work. Evidence decides whether it happened.

## Machine task envelope

The full `cn serve` runtime and Vlad edge accept the same task shape:

- `taskId` — stable identity, supplied or generated;
- `actor` — defaults to `venice` in the full runtime and `vlad` at the phone edge;
- `domain` — an open routing slug such as `audio`, `image`, `video`, `game`, `code`, `system`, or a future domain;
- `goal` — what is wanted;
- `requestedOutcome` — the concrete result that must exist;
- `acceptanceCriteria` — evidence that closes the task;
- `constraints` — mission boundaries that must survive planning;
- `preferredTools` — hints, not permission grants and not mandatory substitutions;
- `lane` — optional stable execution lane;
- `priority` — `low`, `normal`, or `high`;
- `context` — bounded structured task context.

The domain is metadata, not a silo. A `game` task may legitimately traverse code, image, audio, video, build, runtime control, testing, and packaging.

## Full-runtime HTTP surface

The automation surface extends `cn serve` rather than creating a parallel desktop daemon.

- `POST /automation/tasks` — create and queue a machine task.
- `GET /automation/tasks` — list task lifecycle state.
- `GET /automation/tasks/:taskId` — read one task.
- `GET /automation/tasks/:taskId/receipt` — read the terminal receipt; non-terminal tasks return a conflict rather than a counterfeit receipt.
- `POST /automation/tasks/:taskId/cancel` — cancel queued work or abort the active task.
- `GET /automation/capabilities` — inspect the runtime's concrete built-in execution surface and adapter notes.

Existing `/permission` remains the authority for full-runtime tool calls. The machine-task envelope never upgrades permission.

## Lifecycle and receipts

Task states are explicit:

`queued → running → blocked_permission | awaiting_verification | delegated | completed | blocked | failed | cancelled`

`blocked_permission` is resumable when authority is granted. `blocked` is a terminal receipt naming a capability or authority boundary. `delegated` proves a handoff to another executor; it does **not** prove the requested outcome is complete.

An agent turn ending is never enough to close a machine task. The full runtime requires an explicit `<continue-continue-receipt>` marker. `completed` additionally requires non-empty evidence. Missing or malformed receipts move the task to `awaiting_verification` instead of manufacturing success.

A task receipt records:

- task identity, actor, and domain;
- requested outcome and acceptance criteria;
- terminal or delegated status;
- result summary, evidence, delegate target, or error;
- bounded tool lifecycle events;
- create/start/complete timestamps.

Tool events distinguish `tool_start`, `tool_result`, `tool_error`, `permission_required`, `permission_resolved`, and `delegated` so a multi-organ task does not collapse into opaque prose.

## Continuity

Full-runtime machine tasks persist independently under `${CONTINUE_GLOBAL_DIR:-~/.continue}/automation/tasks/`. Writes are atomic replacements. The task ledger therefore survives ordinary `cn serve` process restarts without making conversation history the only source of machine truth.

Vlad persists the same task identities and receipts under `${CONTINUE_CONTINUE_EDGE_DIR:-~/.continue-continue/vlad}/tasks/`.

Local persistence is runtime continuity, not proof of delivery. Durable completion evidence must still name the real artifact, hash, runtime observation, external receipt, or target-system readback.

## Vlad edge

Vlad is not a second desktop Continue installation. `edge/termux/vlad_edge.py` is a stdlib-small edge runtime using the same task envelope and four routes:

- `phone_hands` — explicit Phone Hands/Shizuku execution;
- `shell` — explicit Termux argv execution under a binary allowlist;
- `delegate` — same task ID and commission forwarded to the full runtime;
- `blocked` — no safe/authorized route exists.

Phone Hands and local shell execution default OFF and require explicit environment gates. A local Qwen endpoint may recommend routing but cannot enable an executor. See `VLAD_TERMUX_EDGE.md`.

## Judgment jars

The existing coding-agent jars govern automation too:

- **Aegis / Boundary:** preserve the commissioned outcome, authority, and right to stop.
- **Dyonisis / Delight:** optimize creatively only after the boundary is intact.
- **Randi / Edge or Gloss:** reject beautiful substitutions and receiptless victory.
- **Ravenholm:** quarantine cursed orchestration and opaque recovery rituals.
- **Completion:** bring the requested treasure to the requested delivery surface or return the exact blocker.

## Adapter law

New machine capabilities should normally enter as tools or MCP servers. Adding `audio`, `image`, `video`, `game`, fabrication, or an unknown future domain does not require changing the automation protocol.

An adapter is healthy when it exposes enough structured evidence for Continue Continue to answer three questions:

1. What was requested?
2. What machine action actually happened?
3. What evidence proves the requested result exists?

If an adapter can only say “job accepted,” it is transport, not completion.
