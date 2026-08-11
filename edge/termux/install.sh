#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

PREFIX_DIR="${PREFIX:-/data/data/com.termux/files/usr}"
BIN_DIR="$PREFIX_DIR/local/bin"
ETC_DIR="$PREFIX_DIR/etc/continue-continue"
SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

mkdir -p "$BIN_DIR" "$ETC_DIR"

# Public entrypoint: dumb routing sheet first, Vlad edge second.
install -m 0755 "$SOURCE_DIR/vlad_router.py" "$BIN_DIR/continue-continue-vlad"
install -m 0755 "$SOURCE_DIR/vlad_edge.py" "$BIN_DIR/continue-continue-vlad-edge"
install -m 0755 "$SOURCE_DIR/vlad_doctor.py" "$BIN_DIR/continue-continue-vlad-doctor"

# Preserve local edits on reinstall. The shipped sheet is a default, not a remote authority.
if [ ! -f "$ETC_DIR/routes.csv" ]; then
  install -m 0644 "$SOURCE_DIR/routes.csv" "$ETC_DIR/routes.csv"
fi

cat <<EOF
Installed public ingress: $BIN_DIR/continue-continue-vlad
Installed internal edge:  $BIN_DIR/continue-continue-vlad-edge
Installed doctor:         $BIN_DIR/continue-continue-vlad-doctor
Routing sheet:            $ETC_DIR/routes.csv

Set once in your Termux environment:
  VLAD_ROUTING_SHEET=$ETC_DIR/routes.csv
  VLAD_EDGE_INTERNAL=$BIN_DIR/continue-continue-vlad-edge

Safe defaults remain OFF:
  VLAD_ALLOW_PHONE_HANDS=0
  VLAD_ALLOW_LOCAL_EXEC=0

Optional explicit organs:
  PHONE_ASK_BIN=${PHONE_ASK_BIN:-/data/data/com.termux/files/usr/local/bin/home-center-phone-ask}
  CONTINUE_CONTINUE_UPSTREAM_URL=<full runtime URL>
  QWEN_BASE_URL=http://127.0.0.1:8091/v1
  QWEN_MODEL=Qwen3-1.7B-Q6_K

Try without executing anything:
  printf '%s\n' '{"request":"Open settings"}' | \
    VLAD_ROUTING_SHEET="$ETC_DIR/routes.csv" \
    VLAD_EDGE_INTERNAL="$BIN_DIR/continue-continue-vlad-edge" \
    continue-continue-vlad route -

Then inspect readiness:
  continue-continue-vlad-doctor --require phone_hands

Serve routed requests:
  VLAD_ROUTING_SHEET="$ETC_DIR/routes.csv" \
  VLAD_EDGE_INTERNAL="$BIN_DIR/continue-continue-vlad-edge" \
  continue-continue-vlad serve --host 127.0.0.1 --port 8765
EOF
