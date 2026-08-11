---
name: Ravenholm Process Sanity
description: Quarantine cursed complexity before it becomes the maintenance strategy
---

Review changed code for complexity that is opaque, recovery-hostile, difficult to test, or dependent on heroic operator knowledge. Pay special attention to parallel state machines, hidden provider fallback, duplicated orchestration, mutable global state, undocumented recovery rituals, and abstractions that exist only to support hypothetical future work.

Prefer the smallest reversible seam that preserves the requested capability. Do not remove necessary complexity merely to reduce line count; reject complexity that cannot explain its ownership, failure mode, recovery path, and acceptance test.
