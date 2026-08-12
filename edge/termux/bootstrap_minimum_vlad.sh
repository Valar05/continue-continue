#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SOURCE_DIR/../.." && pwd)"

fail() {
  printf '[blocked] %s\n' "$*" >&2
  exit 3
}

command -v git >/dev/null 2>&1 || fail "git is required on Vlad"

HEAD="$(git -C "$REPO_ROOT" rev-parse HEAD 2>/dev/null || true)"
[ -n "$HEAD" ] || fail "bootstrap must run from the Continue Continue git checkout"

printf '[vlad-minimum] source_head=%s\n' "$HEAD"
printf '[vlad-minimum] stage=install-exact-fork-cn\n'
"$SOURCE_DIR/install_cn_from_source.sh"

printf '[vlad-minimum] stage=install-vlad-edge\n'
"$SOURCE_DIR/install.sh"

printf '[vlad-minimum] stage=configure-local-ollama-coder\n'
vlad bootstrap "$@"

printf '[vlad-minimum] stage=prove-coder-readiness\n'
VLAD_ALLOW_LOCAL_EXEC=1 vlad doctor --require continue

cat <<'EOF'
[vlad-minimum] READY FOR FIRST AUTHORED CANARY
Run the canary from a disposable git repository first:
  VLAD_ALLOW_LOCAL_EXEC=1 vlad code --auto "Create canary.txt containing exactly VLAD_CAN_CODE, then run git diff --check and report the evidence."

After that succeeds, stop using the outside coding path for work Vlad can perform.
EOF
