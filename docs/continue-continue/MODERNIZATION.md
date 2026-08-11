# Continue Continue Modernization Ledger

## Baseline

- Upstream: `continuedev/continue`
- Fork: `Valar05/continue-continue`
- Baseline commit: `5522c6f44ca0ac3528b37244818fbfa39b5af470`
- License: Apache-2.0; upstream notices remain authoritative.

The upstream README describes this codebase as the final 2.0.0-era open-source coding-agent foundation. Continue Continue treats that code as inherited capability, not evidence that every path meets this fork's standards.

## Mission

Keep the useful Continue CLI / VS Code / JetBrains architecture, while making the baseline:

1. local-first and provider-explicit;
2. governed by mission-boundary and evidence rules;
3. testable without paid model calls;
4. recovery-friendly rather than ritual-driven;
5. accessible and inspectable;
6. honest about requested, implemented, deployed, and verified state.

## Phase 0 — constitutional hardening

Acceptance:

- root `AGENTS.md` is loaded by Continue's existing agent-file mechanism;
- Continue-native rules and PR checks encode mission boundary, evidence, local-first behavior, and Ravenholm process sanity;
- new assistant starter config contains a local Ollama model and no cloud API-key placeholders;
- repository CI verifies the standards package and local-first starter invariants.

## Phase 1 — runtime local-first audit

Audit model discovery, onboarding, CLI startup, authentication remnants, telemetry/network calls, provider fallback, embeddings/reranking, and autocomplete. Classify each network dependency as required, optional, stale, or removable. Add offline tests before changing behavior.

## Phase 2 — provider boundary

Create an explicit provider capability boundary so local and remote providers share contracts without implicit fallback. A provider failure must name the failing provider and preserve work. No paid-provider escalation without explicit selection.

## Phase 3 — receipts and recoverability

For agent mutations, preserve enough structured evidence to answer: requested action, files changed, commands run, tests executed, result, unresolved risks, and recovery path. Do not confuse transport success with functional acceptance.

## Phase 4 — accessibility and interaction

Audit keyboard-only navigation, screen-reader semantics, focus management, terminal/TUI output order, nonvisual status reporting, and error recovery. Accessibility is acceptance criteria for the main product, not a separate reduced interface.

## Upstream policy

Track upstream only when useful. Upstream changes are evidence and optional supply, not automatic authority over the fork. Rebase/cherry-pick intentionally, record the source SHA, and run this fork's checks before promotion.
