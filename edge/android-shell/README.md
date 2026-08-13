# Anvil Shell

Anvil Shell is the native Android shell organism that replaces Termux as the human-facing owner while preserving Termux as a compatibility body during migration.

Checkpoint 1 implements source only:

- a disposable Activity and separate `:engine` foreground-service process;
- a SQLite/WAL job and event ledger in device-protected storage;
- idempotency-key conflict detection;
- crash recovery from `CLAIMED/RUNNING/DISPATCHED` to `RECOVERABLE`;
- visible `[anvil][owner][team][state]` markers with screen-reader descriptions;
- a model-free native self-check;
- a typed registry for Adam, Vlad notes, sessions, anvils, explicit shell work, Hunger, Hyperbolic, and Hugging Face;
- deterministic offline Adam quotations from source-carrying public-domain Scripture, literature, and history;
- a narrowly scoped Termux `RUN_COMMAND` compatibility adapter;
- pinned-revision, allow-pattern, SHA-256 requirements for Hugging Face assets.

It does **not** yet claim:

- an installed or callable APK on Drew's phone;
- complete Termux capability replacement;
- a terminal-stream result receiver;
- a native PTY, package repository, toolchain, SSH, X11, Android API bridge, boot resurrection, Home Center adapter, local model runtime, Hunger execution, or Hyperbolic execution;
- phone build, phone restart recovery, or human acceptance.

Build preflight:

```sh
gradle -p edge/android-shell :app:testDebugUnitTest :app:assembleDebug --no-daemon
```

Repository/CI builds are source evidence only. Acceptance requires the exact phone lane and a durable Home Center readback receipt.

Human-facing quote check:

```sh
adam quote --category bible
adam quote --seed 'anvil-shell|checkpoint-1' --json
```

A bare interactive `adam` prints one quote selected from the day, anvil, team, and working-directory seed. Explicit `--seed` makes the selection exactly replayable. Quote output is never injected into shell stdout, receipts, or machine commands.
