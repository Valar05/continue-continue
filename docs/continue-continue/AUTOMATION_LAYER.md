# Continue Continue — Venice Machine Automation Layer

## Mission

Continue Continue is the automation layer for machine work initiated by Venice.

It owns **orchestration**: task boundaries, sequencing, tool selection, permission handoff, lifecycle state, evidence, receipts, and exact blocking boundaries.

It does **not** replace the execution organs. Existing specialized systems remain authoritative for the work they actually perform: Home Center / Computer Hands, MCP servers, shells, FFmpeg, renderers, image systems, game engines, DCC tools, local models, and future adapters.

The compact law is:

> Venice asks for an outcome. Continue Continue runs the machine plan. Specialized organs do the physical work. Evidence decides whether it happened.

## Machine task envelope

`cn serve` exposes a typed automation API. A task contains:

- `taskId` — stable identity, supplied or generated;
- `actor` — defaults to `venice`;
- `domain` — an open routing slug such as `audio`, `image`, `video`, `game`, `code`, `system`, or a future domain;
- `goal` — what Venice wants done;
- `requestedOutcome` — the concrete result that must exist;
- `acceptanceCriteria` — evidence that closes the task;
- `constraints` — mission boundaries that must survive planning;
- `preferredTools` — hints, not permission grants and not mandatory substitutions;
- `lane` — optional stable execution lane;
- `priority` — `low`, `normal`, or `high`;
- `context` — bounded structured task context.

The domain is metadata, not a silo. A `game` task may legitimately traverse code, image, audio, video, build, runtime control, testing, and packaging.

## HTTP surface

The automation surface extends `cn serve` rather than creating a parallel daemon.

- `POST /automation/tasks` — create and queue a machine task.
- `GET /automation/tasks` — list task lifecycle state.
- `GET /automation/tasks/:taskId` — read one task.
- `GET /automation/tasks/:taskId/receipt` — read the terminal receipt; non-terminal tasks return a conflict rather than a counterfeit receipt.
- `POST /automation/tasks/:taskId/cancel` — cancel queued work or abort the active task.
- `GET /automation/capabilities` — inspect connected MCP tools plus built-in execution tools.
- `GET /state` — includes the current automation ledger beside ordinary agent state.

Existing `/permission` remains the permission authority for tool calls. The machine-task envelope never upgrades permission.

## Lifecycle

Task states are explicit:

`queued → running → blocked | paused | completed | failed | cancelled`

`blocked` is not failure. It means Continue Continue reached a permission or capability boundary and still knows what would be required to proceed.

A task receipt records:

- task identity, actor, and domain;
- requested outcome and acceptance criteria;
- terminal status;
- result summary or error;
- bounded tool lifecycle events;
- create/start/complete timestamps.

Tool events distinguish `tool_start`, `tool_result`, `tool_error`, `permission_required`, and `permission_resolved` so a multi-organ task does not collapse into opaque prose.

## Continuity

Automation records ride inside the existing long-lived Continue session. `cn serve --id <stable-id>` restores the task ledger with the same session history. Storage-sync snapshots also expose the ledger through `/state`.

Session persistence is runtime continuity, not proof of delivery. Durable completion evidence should still name the real artifact, hash, runtime observation, external receipt, or target-system readback.

## Judgment jars

The existing coding-agent jars govern automation too:

- **Aegis / Boundary:** preserve the commissioned outcome, authority, and right to stop.
- **Dyonisis / Delight:** optimize creatively only after the boundary is intact.
- **Randi / Edge or Gloss:** reject beautiful substitutions and receiptless victory.
- **Ravenholm:** quarantine cursed orchestration and opaque recovery rituals.
- **Completion:** bring the requested treasure to the requested delivery surface or return the exact blocker.

## Adapter law

New machine capabilities should normally enter as tools or MCP servers. Adding `audio`, `image`, `video`, or `game` capability does not require changing the automation protocol.

An adapter is healthy when it exposes enough structured evidence for Continue Continue to answer three questions:

1. What was requested?
2. What machine action actually happened?
3. What evidence proves the requested result exists?

If an adapter can only say “job accepted,” it is transport, not completion.
