# Anvil Shell — Termux capability preservation and replacement contract

## Commission

Drew commissioned a shell app that keeps what Termux provides while becoming less fragile, rolls in his deterministic CLI tools, runs Hunger and Hyperbolic through their real governing organs, supports team/tmux-style markers, and researches Hugging Face imports.

The product name for this branch is **Anvil Shell**. Adam remains the deterministic human command surface. Vlad remains the model-bearing machine/judgment helper. Home Center remains the durable coordination and readback spine. Termux is a compatibility runtime during migration, not the state owner.

## Hunger ruling

Android process death is a reachable product state, not an exception. Anvil Shell uses **resurrective work**, not an invulnerability claim:

1. write the immutable request before execution;
2. claim by compare-and-set;
3. append every transition;
4. checkpoint finite work;
5. after process death, mark uncertain work `RECOVERABLE`;
6. reconcile before rerun;
7. never convert a dispatch receipt into a completion receipt.

The Save Point mechanism fits because recovery begins from an explicit durable boundary. It predicts the wrong thing if interpreted as full rollback: external shell side effects may already have happened, so restart requires reconciliation, not blind replay.

Resurrective Immortality fits because the worker body may die while the job identity survives. It predicts the wrong thing if interpreted as process preservation: Android still owns process lifetime.

Hive Mind is rejected as the governing model. Multiple UI, worker, Termux, Home Center, and local-model bodies do not share omniscient state. They are typed organs consuming one event spine. Killing one organ must not destroy ownership or evidence.

## Android architecture

- `MainActivity` is disposable and never owns work.
- `ShellSupervisorService` runs in `:engine` only while user-visible work needs it.
- SQLite/WAL in device-protected storage owns jobs and append-only events.
- Finite jobs are idempotent and resumable.
- Interactive shell work is visibly classified `PHONE_INTERACTION`.
- Diagnostics and maintenance remain separate planes.
- Hunger/Hyperbolic are `JUDGMENT` operations routed to Home Center; they are never aliases for local prompt text or raw shell.
- `tmux` may preserve live terminal ergonomics when available, but SQLite checkpoints and receipts remain authoritative.
- Team markers are explicit data: anvil, owner, team/worker, state, command ID, route, and receipt identity.

## Termux capability ledger

The replacement remains incomplete until each capability is either native, preserved by a verified adapter, or explicitly rejected with a migration path:

| Capability | Checkpoint 1 | Required acceptance |
|---|---|---|
| Terminal UI and extra keys | Not implemented | Native accessible PTY UI; touch/keyboard/screen-reader parity |
| POSIX shell and core tools | Termux adapter only | Native or packaged runtime with exact version/hash receipt |
| `pkg/apt` repositories | Not implemented | Signed, pinned repository/bootstrap with rollback |
| Python, Node, Java, C/C++, Git | Not implemented | Phone diagnostics plus build/run canaries |
| SSH and long-running daemons | Not implemented | Foreground/restart policy and liveness receipts |
| Sessions / tmux | Typed session verbs only | Attach/detach/checkpoint/resume/kill tests |
| Storage access | App-private ledger only | SAF-scoped project roots; no broad traversal |
| Termux:API device commands | Preserved conceptually | Native typed Android adapters or verified compatibility |
| Boot tasks / widgets / shortcuts | Not implemented | Explicit user-visible recovery and accessibility tests |
| X11 / GUI forwarding | Not implemented | Optional organ; never baseline shell readiness |
| Home Center / Phone Hands | Typed seam only | Exact deployed adapter and readback |
| Adam / Vlad / Continue | Registry plus Termux compatibility | Native invocation and real phone receipts |
| Hunger / Hyperbolic | Registered, fail-closed | Home Center Drive truth + Jar receipt + terminal result |

## Deterministic CLI surface

The registry includes:

- `status`, `doctor`;
- `session.list/open/checkpoint/resume/stop`;
- `anvil.select/stream`;
- `adam.doctor/status/quote`;
- `vlad.notes.status/compile/query/next/receipt`;
- explicit `shell.exec`;
- `hunger.invoke`, `hyperbolic.invoke`;
- `hf.status/import/verify/bench`.

Unknown free text blocks. It never becomes shell or model input by convenience.

`adam quote` is a model-free offline organ with three corpus categories: `bible`, `literature`, and `history`. Selection is SHA-256-derived from an explicit seed or from day + anvil + team + working directory. The same seed and category always produce the same record. Human interactive startup may print a quotation; machine commands and receipts never receive unsolicited prose. Each record carries an attribution, work/reference, and source URL. The initial corpus uses public-domain KJV Scripture and public-domain literary/historical texts.

The new stdlib-only `vlad-notes` executable finally implements the previously promised five verbs. It scans only the approved project root and allowlisted doctrine paths, rejects symlinks and suspicious names, redacts likely secret assignments, writes an atomic hashed context pack, performs deterministic text lookup, extracts explicit gates/actions, and appends hash-chained decision receipts.

## Hugging Face research and import law

Hugging Face is optional inventory. It cannot sit on the deterministic route.

Candidate phone experiments:

1. `Qwen/Qwen2.5-Coder-1.5B-Instruct-GGUF` — compare against the existing local Qwen body for bounded code explanation and review. Do not grant shell authority.
2. `HuggingFaceTB/SmolLM2-360M-Instruct-GGUF` — tiny classifier/adviser experiment only if measured latency and quality beat deterministic CSV routing for a declared fallback.
3. `HuggingFaceTB/SmolLM2-1.7B-Instruct-GGUF` — optional general local adviser benchmark; never a readiness dependency.
4. `google/gemma-3n-E2B-it-litert-lm` — Android-native multimodal research candidate, but its multi-gigabyte footprint makes it a poor first shell organ.
5. Terminal-bench and Unix-command datasets — adversarial fixture sources only. They may test that dangerous or ambiguous prose does not auto-execute; dataset text never becomes an allowlist.

Every import requires:

- repository ID and immutable 40-character revision;
- explicit allowed filenames/patterns;
- license and provenance review;
- expected file SHA-256 values;
- byte budget, storage target, and rollback identity;
- phone-local cold/warm latency, peak RSS, battery, thermal, and usefulness measurements;
- no token, credential, provider, or network dependency after verified import.

## Current evidence state

| State | Truth |
|---|---|
| Requested | Yes |
| Architecture researched | Yes |
| Implemented source | Checkpoint 1 on `agent/anvil-shell-organism` |
| Repository tested | CI-gated per exact commit; the latest green source checkpoint before Regnet repair was `e0bb1a79041e7d7d001545d77cb5281714803875` in [run 31709121997](https://github.com/Valar05/continue-continue/actions/runs/31709121997) |
| APK artifact | CI source-checkpoint artifact only; never phone proof |
| Installed phone | No |
| Callable phone | No |
| Complete Termux replacement | No |
| Delivered | No |
| Human accepted | No |

## Next falsifiable checkpoint

1. repository build and deterministic CLI/unit tests pass at exact head, including same-seed quote replay and category filtering;
2. absolute Termux executable paths, Adam quote dispatch, and Android manifest contracts are verified;
3. APK is built on `primary-phone` through the authorized phone build plane;
4. APK installs with exact package/signer/hash receipt;
5. queue a native self-check, kill the Activity, read `SUCCEEDED`;
6. kill `:engine` during a fixture, restart, read `RECOVERABLE`, reconcile once;
7. execute one harmless `adam doctor` through the Termux compatibility adapter and receive a terminal result receipt;
8. prove screen-reader access to status, stop, recovery, and error controls;
9. deliver the Home Center readback receipt.

No repository or CI result may be promoted past implemented/tested source.
