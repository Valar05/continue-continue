---
name: Local First
description: Prevent hidden cloud or metered dependencies from entering the baseline coding path
---

Review changed configuration, onboarding, model selection, networking, telemetry, and fallback behavior. Fail if a previously local-capable baseline now requires a hosted account, API key, paid/metered provider, or network access without an explicit approved product decision.

Remote providers may be added as opt-in integrations. Require provider choice to remain visible and require failure to be explicit rather than silently falling through to another provider.
