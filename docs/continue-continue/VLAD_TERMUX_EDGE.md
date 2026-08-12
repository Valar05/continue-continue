# Vlad Termux Edge

Vlad is the small Android/Termux body of Continue Continue. It speaks the same machine-task contract as the full runtime but does not carry the VS Code, JetBrains, or full Node dependency graph.

## Role

Vlad may route a machine task to one of four outcomes:

- `phone_hands` — use the proven Home Center Phone Hands/Shizuku body;
- `shell` — execute an explicit argv action in Termux when local execution has been enabled;
- `delegate` — preserve the task ID and hand the unchanged commission to a configured full Continue Continue runtime;
- `blocked` — stop at the missing capability or authority boundary.

The task domain remains open-ended. Audio, image, video, game, code, system, fabrication, shader work, and future domains use the same envelope. The domain does not grant a tool or imply that the phone can perform that work locally.

## Authority

Task intent is not permission.

Phone Hands requires `VLAD_ALLOW_PHONE_HANDS=1`. Local command execution requires `VLAD_ALLOW_LOCAL_EXEC=1` and the executable must be present in `VLAD_ALLOWED_BINS`. Delegation requires an explicitly configured `CONTINUE_CONTINUE_UPSTREAM_URL`.

A local Qwen endpoint may recommend `phone_hands`, `delegate`, or `blocked`, but the recommendation never enables an executor. Default local route settings are compatible with the existing Android executive:

- `QWEN_BASE_URL=http://127.0.0.1:8091/v1`
- `QWEN_MODEL=Qwen3-1.7B-Q6_K`
- `PHONE_ASK_BIN=/data/data/com.termux/files/usr/local/bin/home-center-phone-ask`

## Delegation law

Delegation preserves:

- task ID;
- actor;
- requested outcome;
- constraints;
- acceptance criteria;
- lane and delivery context.

A `delegated` receipt proves the handoff, not the requested outcome. Only the full runtime's later evidence-backed completion receipt closes the work.

## Durable state

Vlad writes task records and receipts under `${CONTINUE_CONTINUE_EDGE_DIR:-~/.continue-continue/vlad}/tasks`. Writes are atomic temp-file replacements. This state is local runtime evidence; promotion or cross-device completion still requires the requested durable/target-system receipt.

## Install

From the repository checkout in Termux:

```bash
bash edge/termux/install.sh
```

The installed command is `continue-continue-vlad`.

## Interfaces

One-shot:

```bash
continue-continue-vlad run task.json
```

Service:

```bash
continue-continue-vlad serve --host 127.0.0.1 --port 8765
```

The service exposes the same core surface as the full runtime:

- `GET /automation/capabilities`
- `GET /automation/tasks`
- `POST /automation/tasks`
- `GET /automation/tasks/:taskId`
- `GET /automation/tasks/:taskId/receipt`

Vlad intentionally has fewer executors. Same language, smaller body.
