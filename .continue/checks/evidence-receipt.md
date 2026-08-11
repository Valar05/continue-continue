---
name: Evidence Receipt
description: Reject completion claims that outrun the evidence produced by the change
---

Review the changed files and PR claims. Look for receiptless victory: implemented code described as deployed, a successful transport described as functional acceptance, generated output described as correct without checking it, or tests that assert plumbing while the user-visible behavior remains unverified.

Require the strongest practical evidence for the claimed state. If the PR cannot produce that evidence yet, require the claim to be downgraded to implemented, proposed, or blocked rather than pretending completion.
