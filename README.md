<h1 align="center">Continue Continue</h1>

<p align="center">A local-first machine automation agent built from the open-source Continue foundation.</p>

## Why this fork exists

`continuedev/continue` ended its actively maintained coding-agent line with the 2.0.0-era codebase and explicitly invited others to use it as a foundation. Continue Continue takes that foundation seriously: keep the useful CLI, IDE, model, MCP, and tool architecture, then harden the agent around explicit authority, local-first operation, recoverability, and evidence-backed completion.

The foundational role is now broader than coding: **Continue Continue is the automation layer for machine work initiated by Venice.** Audio, image, video, games, code, system control, and future machine domains all enter through one task/receipt contract. Specialized tools remain specialized execution organs underneath it.

This is a real GitHub fork. Upstream remains `continuedev/continue`; the initial modernization baseline is commit `5522c6f44ca0ac3528b37244818fbfa39b5af470`.

## Current divergence

Continue Continue now hardens five seams:

- generated assistant configuration is **local-first** with Ollama rather than teaching cloud API keys by default;
- a root agent constitution is loaded by Continue as an always-on workspace rule;
- Continue-native rules/checks enforce mission boundaries, evidence receipts, local-first behavior, and Ravenholm process sanity;
- inherited publication automation is quarantined behind explicit dispatch rather than firing from ordinary repository events;
- `cn serve` is becoming the machine automation service: typed task identity, domain-open routing, lifecycle state, permission blocking, capability discovery, cancellation, and terminal receipts over existing tools/MCP executors.

See [`docs/continue-continue/AUTOMATION_LAYER.md`](docs/continue-continue/AUTOMATION_LAYER.md) for the machine-task contract, [`docs/continue-continue/MODERNIZATION.md`](docs/continue-continue/MODERNIZATION.md) for the phased engineering ledger, and [`docs/continue-continue/JUDGMENT_JARS.md`](docs/continue-continue/JUDGMENT_JARS.md) for the decision operators.

## Machine automation law

Venice asks for an outcome. Continue Continue owns orchestration. Specialized organs do the physical work. Evidence decides whether it happened.

A task domain such as `audio`, `image`, `video`, `game`, `code`, or `system` is routing metadata, not a silo. A game task may legitimately cross code, image, sound, render, build, runtime control, and testing.

The automation envelope never grants tool permission. Existing tool/MCP permission policy remains controlling. Missing capability becomes `blocked`; it does not become an excuse to return a nearby artifact.

## Operating law

An agent may improve the means aggressively. It may not silently change the commissioned outcome, owner, execution lane, exclusions, evidence standard, or delivery surface.

Two failures are hard gates:

- **Beautiful substitution:** a polished adjacent solution hides a changed mission.
- **Receiptless victory:** a confident completion claim outruns the artifact or read-back evidence.

Local models are the baseline. Remote providers remain supported integrations, but they are opt-in capability rather than the price of admission.

## Components inherited from Continue

- CLI and long-lived `serve` mode
- VS Code extension
- JetBrains plugin
- model/provider abstraction
- MCP and tool calling
- tool permission policy
- workspace rules and agent files
- Continue checks

The inherited code is capability, not automatic acceptance. Each path is audited and promoted under this fork's standards.

## Development

Run the fork-specific invariant check without installing provider SDKs or spending model tokens:

```bash
node scripts/verify-continue-continue-standards.mjs
```

Existing upstream build and test documentation remains in [`TESTING.md`](TESTING.md) and the component directories while the modernization ledger replaces stale assumptions incrementally.

## Upstream and license

Continue Continue is derived from [Continue](https://github.com/continuedev/continue) and retains the upstream Apache-2.0 license and notices.

Apache 2.0 © 2023-2026 Continue Dev, Inc. and contributors. Fork modifications © their respective contributors.
