#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

PREFIX_DIR="${PREFIX:-/data/data/com.termux/files/usr}"
BIN_DIR="$PREFIX_DIR/local/bin"
ETC_DIR="$PREFIX_DIR/etc/continue-continue"
SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

mkdir -p "$BIN_DIR" "$ETC_DIR"

# Internal organs.
install -m 0755 "$SOURCE_DIR/vlad_router.py" "$BIN_DIR/continue-continue-vlad-router"
install -m 0755 "$SOURCE_DIR/vlad_edge.py" "$BIN_DIR/continue-continue-vlad-edge"
install -m 0755 "$SOURCE_DIR/vlad_doctor.py" "$BIN_DIR/continue-continue-vlad-doctor"
install -m 0755 "$SOURCE_DIR/vlad_continue_bootstrap.py" "$BIN_DIR/continue-continue-vlad-bootstrap"
install -m 0755 "$SOURCE_DIR/vlad_cli.py" "$BIN_DIR/continue-continue-vlad-cli"
install -m 0755 "$SOURCE_DIR/vlad_notes.py" "$BIN_DIR/vlad-notes"
install -m 0755 "$SOURCE_DIR/adam_doctor.py" "$BIN_DIR/continue-continue-adam-doctor"
install -m 0755 "$SOURCE_DIR/adam_cli.py" "$BIN_DIR/continue-continue-adam-cli"
install -m 0755 "$SOURCE_DIR/codex_worker.py" "$BIN_DIR/continue-continue-codex-worker"
install -m 0644 "$SOURCE_DIR/adam_quotes.py" "$BIN_DIR/adam_quotes.py"

# Preserve local edits on reinstall. The shipped sheet is a default, not a remote authority.
if [ ! -f "$ETC_DIR/routes.csv" ]; then
  install -m 0644 "$SOURCE_DIR/routes.csv" "$ETC_DIR/routes.csv"
fi

# Stable machine entrypoint. Routing sheet is always evaluated before Vlad edge.
cat > "$BIN_DIR/continue-continue-vlad" <<EOF
#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
export VLAD_ROUTING_SHEET="\${VLAD_ROUTING_SHEET:-$ETC_DIR/routes.csv}"
export VLAD_EDGE_INTERNAL="\${VLAD_EDGE_INTERNAL:-$BIN_DIR/continue-continue-vlad-edge}"
exec "$BIN_DIR/continue-continue-vlad-router" "\$@"
EOF
chmod 0755 "$BIN_DIR/continue-continue-vlad"

# Vlad owns model-backed judgment and Continue/Ollama readiness.
cat > "$BIN_DIR/vlad" <<EOF
#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
if [ "\${1:-}" = "bootstrap" ]; then
  shift
  exec "$BIN_DIR/continue-continue-vlad-bootstrap" "\$@"
fi
exec "$BIN_DIR/continue-continue-vlad-cli" "\$@"
EOF
chmod 0755 "$BIN_DIR/vlad"

# Adam is the human-facing phone daemon. It performs no model inference itself;
# shell/Continue/phone work is routed through deterministic commands and Vlad.
cat > "$BIN_DIR/adam" <<EOF
#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
export ADAM_BIN="\${ADAM_BIN:-$BIN_DIR/adam}"
export ADAM_DOCTOR_BIN="\${ADAM_DOCTOR_BIN:-$BIN_DIR/continue-continue-adam-doctor}"
export ADAM_VLAD_BIN="\${ADAM_VLAD_BIN:-$BIN_DIR/vlad}"
export ADAM_CODEX_WORKER_BIN="\${ADAM_CODEX_WORKER_BIN:-$BIN_DIR/continue-continue-codex-worker}"
exec "$BIN_DIR/continue-continue-adam-cli" "\$@"
EOF
chmod 0755 "$BIN_DIR/adam"

cat <<EOF
Installed human daemon:   $BIN_DIR/adam
Installed Adam doctor:    $BIN_DIR/continue-continue-adam-doctor
Installed Vlad helper:    $BIN_DIR/vlad
Installed machine ingress:$BIN_DIR/continue-continue-vlad
Installed notes CLI:      $BIN_DIR/vlad-notes
Installed quote corpus:   $BIN_DIR/adam_quotes.py
Installed Codex worker:   $BIN_DIR/continue-continue-codex-worker
Installed routing engine: $BIN_DIR/continue-continue-vlad-router
Installed internal edge:  $BIN_DIR/continue-continue-vlad-edge
Installed Vlad doctor:    $BIN_DIR/continue-continue-vlad-doctor
Installed coder bootstrap:$BIN_DIR/continue-continue-vlad-bootstrap
Routing sheet:            $ETC_DIR/routes.csv

Ownership:
  adam = phone-facing prompt, shell/Continue command surface, routing, policy, receipts; no model inference
  vlad = Ollama/model-backed judgment and Continue model readiness
  venice = optional adviser, never required for Adam readiness

Safe defaults remain OFF:
  VLAD_ALLOW_PHONE_HANDS=0
  VLAD_ALLOW_LOCAL_EXEC=0

First bounded proof:
  adam doctor

Human use:
  adam
  adam quote --category bible
  adam quote --seed 'anvil-shell|checkpoint-1' --json
  adam shell 'git status'
  adam codex doctor
  adam codex 'Inspect this project and return one bounded next action'
  adam codex resume THREAD_ID 'Continue the same bounded task'
  adam code 'Make one bounded change and run its focused test'
  adam review 'Review the current diff'

Vlad remains available as the helper/diagnostic organ:
  vlad doctor --require continue
  vlad bootstrap

Coding remains explicitly gated by Vlad edge. To authorize local Continue work,
VLAD_ALLOW_LOCAL_EXEC must be 1 and cn must remain allowed by VLAD_ALLOWED_BINS.
Adam never enables that gate and never contacts Ollama directly.
EOF