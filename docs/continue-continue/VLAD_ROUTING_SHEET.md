# Vlad routing sheet

Vlad has a deliberately dumb ingress layer in front of the edge runtime.

The public `continue-continue-vlad` command reads a CSV routing sheet before a request reaches `vlad_edge.py`. The sheet is intended to be editable in any spreadsheet program or as plain text. It is deterministic, first-match-wins, and uses lowercase substring matching only.

## Why it exists

Most machine requests are not ambiguous enough to deserve a model call. `Open settings` is a phone action. `Render a video` belongs on the full automation runtime. `Factory reset the phone` should stop before any planner gets clever.

The sheet converts those obvious cases into routing metadata. Qwen is fallback for unmatched requests, not the front door.

## Authority boundary

The routing sheet **does not grant permission**.

- A `phone_hands` row still requires `VLAD_ALLOW_PHONE_HANDS=1`.
- A `shell` row still requires `VLAD_ALLOW_LOCAL_EXEC=1`, and the binary must survive Vlad's allowlist.
- A `delegate` row is a handoff, never completion.
- A `blocked` row produces a blocking receipt rather than substituting another path.
- A caller-provided `context.edge.action` is never overwritten by the sheet.

This preserves the Continue Continue judgment rule: classification may narrow execution, but it cannot launder authority.

## Sheet columns

| Column | Meaning |
| --- | --- |
| `priority` | Integer ordering; lower rows run first. |
| `enabled` | `1`, `true`, `yes`, or `on` enables the row. |
| `name` | Stable human-readable rule name. |
| `domain` | Match one task domain or `*`. |
| `contains_any` | Pipe-separated substrings; at least one must appear. |
| `contains_all` | Pipe-separated substrings; all must appear. |
| `route` | `phone_hands`, `shell`, `delegate`, `blocked`, or `passthrough`. |
| `target_domain` | Optional domain assigned before Vlad sees the task. |
| `command` | Static shell command for a `shell` row. No model-generated shell text is accepted here. |
| `phone_prompt` | Prompt template for Phone Hands. `{goal}`, `{requestedOutcome}`, and `{domain}` are available. |
| `reason` | Durable explanation recorded with the routing decision. |

The shipped sheet lives at `edge/termux/routes.csv`. The installer copies it to `$PREFIX/etc/continue-continue/routes.csv` only when that file does not already exist, so local edits survive reinstall.

## Raw request ingress

The router accepts the normal machine-task envelope or the smaller form:

```json
{"request":"Open settings"}
```

It converts raw requests to an `unsorted` task, applies the sheet, then hands the resulting task to Vlad. A matching rule may assign a real domain such as `system`, `audio`, `video`, or `game`.

## Preview without execution

```sh
printf '%s\n' '{"request":"Open settings"}' | continue-continue-vlad route -
```

The HTTP equivalent is `POST /routing/preview`.

Previewing never executes a machine action.

## Operational invariant

`continue-continue-vlad-doctor` treats a missing, malformed, or empty-enabled routing sheet as a hard readiness failure. If the ingress sheet is broken, Vlad is not ready.
