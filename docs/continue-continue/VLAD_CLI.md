# Vlad CLI

## Mission

`vlad` is the first-class terminal/operator surface for Continue Continue's tiny edge runtime. It exists so machine work remains usable when ChatGPT is absent, and so ChatGPT can multiply an already-usable local operator instead of owning the operator.

`continue-continue-vlad` remains the machine ingress and HTTP/routing surface. `vlad` is a human-facing wrapper around that same authority, routing, evidence, and receipt machinery.

Vlad is **not** another agent, filesystem, control plane, or canonical memory system.

## Human surface

```sh
vlad
vlad status
vlad doctor
vlad "Open settings"
vlad route "Render a short video"
vlad phone "Open Spotify"
vlad observe
vlad home
vlad code "Implement the bounded task"
vlad review "Review the current diff"
```

Bare `vlad` opens a small REPL. Normal lines are machine requests and pass through the CSV routing sheet before the edge runtime. REPL commands include `/doctor`, `/route`, `/code`, `/review`, and `/quit`.

`--json` preserves machine-readable envelopes for orchestration.

## Continue coding seam

Continue remains the requested coding organ.

```sh
vlad code "Implement one focused change"
vlad review "Review the current diff"
vlad code --auto "Implement the already-authorized bounded change"
vlad code --resume "Continue the prior bounded task"
```

The CLI builds an explicit Vlad edge shell action whose argv starts with `cn -p`. Review adds `--readonly`. `--auto` is never implied; it is present only when the caller explicitly supplies it.

The CLI **does not grant local execution authority**. The existing Vlad edge gate still requires `VLAD_ALLOW_LOCAL_EXEC=1`, and `cn` must be allowed by `VLAD_ALLOWED_BINS`. A blocked code request exits blocked; it is not silently delegated to another coding agent.

## Phone seam

`vlad phone`, `vlad observe`, and `vlad home` create explicit `phone_hands` actions, but they do not grant Phone Hands authority. `VLAD_ALLOW_PHONE_HANDS=1` remains the execution gate.

## Exit codes

The public CLI preserves the established Vlad contract:

- `0` success (including a truthful successful handoff receipt)
- `2` bad invocation
- `3` blocked
- `4` execution failure/cancelled
- `5` verification unresolved/failed

## Relationship to Venice

Vlad and Venice are sibling CLIs with different authority.

- Venice owns canonical local speech, durable identity, preference, creative judgment, and what she wants done.
- Vlad owns machine routing, body/device actions, Continue/code work, execution, verification, blocking, and receipts.

Neither parses commands from Venice prose. An orchestrator composes them only through structured task/action data.

## Offline survival

With ChatGPT unavailable, the intended local loop is:

```text
Drew -> venice            conversation / judgment / continuity
Drew -> vlad              machine work / code / phone / verification
venice structured action -> vlad task   optional explicit composition
```

With ChatGPT present, ChatGPT may orchestrate both, but the same commands and evidence paths remain independently usable.

## Acceptance

Repository implementation is not phone deployment. Call `vlad` deployed only after the intended Termux lane proves:

1. `vlad status` resolves the installed machine ingress and doctor;
2. `vlad route` proves the CSV front door is still first;
3. a blocked Phone Hands request exits `3` when permission is disabled;
4. an explicitly enabled harmless Phone Hands request returns a physical receipt;
5. `vlad review` reaches the configured `cn` binary through the Vlad edge and produces a Continue receipt;
6. one bounded `vlad code` change is reviewed and then verified by Mobile Coding Dungeon before being called complete;
7. the same local commands remain usable with ChatGPT unavailable.
