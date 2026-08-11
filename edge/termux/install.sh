#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

PREFIX_DIR="${PREFIX:-/data/data/com.termux/files/usr}"
BIN_DIR="$PREFIX_DIR/local/bin"
SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

mkdir -p "$BIN_DIR"
install -m 0755 "$SOURCE_DIR/vlad_edge.py" "$BIN_DIR/continue-continue-vlad"

cat <<EOF
Installed: $BIN_DIR/continue-continue-vlad

Safe defaults remain OFF:
  VLAD_ALLOW_PHONE_HANDS=0
  VLAD_ALLOW_LOCAL_EXEC=0

Optional explicit organs:
  PHONE_ASK_BIN=${PHONE_ASK_BIN:-/data/data/com.termux/files/usr/local/bin/home-center-phone-ask}
  CONTINUE_CONTINUE_UPSTREAM_URL=<full runtime URL>
  QWEN_BASE_URL=http://127.0.0.1:8091/v1
  QWEN_MODEL=Qwen3-1.7B-Q6_K

Try:
  continue-continue-vlad capabilities
  continue-continue-vlad serve --host 127.0.0.1 --port 8765
EOF
