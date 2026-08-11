---
globs: /**/*
description: Keep the baseline coding loop local-first and make cloud use explicit
---

# Local First

Default new configurations, examples, and recovery paths to locally reachable models and tools when the feature permits it.

Do not introduce a required hosted account, API key, metered provider, telemetry endpoint, or network dependency into a baseline local workflow without an explicit product decision and tests covering the new boundary.

Remote providers remain supported integrations. They are opt-in capability, not the definition of a working installation.

Offline and provider-failure behavior should fail clearly, preserve user work, and never silently switch execution to another paid or remote provider.
