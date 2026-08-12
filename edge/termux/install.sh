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

# First-class human survival surface. Bootstrap is deterministic and local;
# every other command stays on the existing Python CLI and machine ingress.
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

cat <<EOF
Installed human CLI:      $BIN_DIR/vlad
Installed machine ingress:$BIN_DIR/continue-continue-vlad
Installed routing engine: $BIN_DIR/continue-continue-vlad-router
Installed internal edge:  $BIN_DIR/continue-continue-vlad-edge
Installed doctor:         $BIN_DIR/continue-continue-vlad-doctor
Installed coder bootstrap:$BIN_DIR/continue-continue-vlad-bootstrap
Routing sheet:            $ETC_DIR/routes.csv

Safe defaults remain OFF:
  VLAD_ALLOW_PHONE_HANDS=0
  VLAD_ALLOW_LOCAL_EXEC=0

Optional explicit organs:
  PHONE_ASK_BIN=${PHONE_ASK_BIN:-/data/data/com.termux/files/usr/local/bin/home-center-phone-ask}
  CONTINUE_CONTINUE_UPSTREAM_URL=<full runtime URL>
  QWEN_BASE_URL=http://127.0.0.1:8091/v1
  QWEN_MODEL=Qwen3-1.7B-Q6_K
  VLAD_CN_BIN=cn
  VLAD_OLLAMA_URL=http://127.0.0.1:11434
  VLAD_OLLAMA_MODEL=<already-installed Ollama model>

Minimum local coding path:
  vlad bootstrap
  vlad doctor --require continue
  vlad code --auto "Make one bounded change and run its focused test"

Human use:
  vlad
  vlad status
  vlad "Open settings"
  vlad route "Render a short video"
  vlad review "Review the current diff"

Coding remains explicitly gated by Vlad edge. To authorize local Continue work,
VLAD_ALLOW_LOCAL_EXEC must be 1 and cn must remain allowed by VLAD_ALLOWED_BINS.
`vlad bootstrap` never downloads a model and never overwrites a non-empty
Continue config unless --force is explicit.

Machine use:
  printf '%s\n' '{"request":"Open settings"}' | continue-continue-vlad route -
  continue-continue-vlad-doctor --require phone_hands
  continue-continue-vlad serve --host 127.0.0.1 --port 8765
EOF