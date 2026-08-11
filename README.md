<h1 align="center">Continue Continue</h1>

<p align="center">A maintained, local-first continuation of the open-source Continue coding agent.</p>

## Why this fork exists

`continuedev/continue` ended its actively maintained coding-agent line with the 2.0.0-era codebase and explicitly invited others to use it as a foundation. Continue Continue takes that foundation seriously: keep the useful CLI, VS Code, and JetBrains architecture, then harden the agent around explicit authority, local-first operation, recoverability, and evidence-backed completion.

This is a real GitHub fork. Upstream remains `continuedev/continue`; the initial modernization baseline is commit `5522c6f44ca0ac3528b37244818fbfa39b5af470`.

## Current divergence

The first Continue Continue hardening layer does four things:

- makes the generated assistant starter **local-first** with Ollama rather than teaching cloud API keys by default;
- installs a root agent constitution that Continue already knows how to load as an always-on workspace rule;
- adds Continue-native rules/checks for mission boundaries, evidence receipts, local-first behavior, and Ravenholm process sanity;
- adds a zero-provider-cost CI check that prevents those guarantees from quietly disappearing.

See [`docs/continue-continue/MODERNIZATION.md`](docs/continue-continue/MODERNIZATION.md) for the phased engineering ledger and [`docs/continue-continue/JUDGMENT_JARS.md`](docs/continue-continue/JUDGMENT_JARS.md) for the decision operators.

## Operating law

A coding agent may improve the means aggressively. It may not silently change the commissioned outcome, owner, execution lane, exclusions, evidence standard, or delivery surface.

Two failures are hard gates:

- **Beautiful substitution:** a polished adjacent solution hides a changed mission.
- **Receiptless victory:** a confident completion claim outruns the artifact or read-back evidence.

Local models are the baseline. Remote providers remain supported integrations, but they are opt-in capability rather than the price of admission.

## Components inherited from Continue

- CLI
- VS Code extension
- JetBrains plugin
- model/provider abstraction
- workspace rules and agent files
- Continue checks

The inherited code is capability, not automatic acceptance. Each path is being audited and promoted under this fork's standards.

## Development

Run the fork-specific invariant check without installing provider SDKs or spending model tokens:

```bash
node scripts/verify-continue-continue-standards.mjs
```

Existing upstream build and test documentation remains in [`TESTING.md`](TESTING.md) and the component directories while the modernization ledger replaces stale assumptions incrementally.

## Upstream and license

Continue Continue is derived from [Continue](https://github.com/continuedev/continue) and retains the upstream Apache-2.0 license and notices.

Apache 2.0 © 2023-2026 Continue Dev, Inc. and contributors. Fork modifications © their respective contributors.
