#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

PREFIX_DIR="${PREFIX:-/data/data/com.termux/files/usr}"
SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SOURCE_DIR/../.." && pwd)"
CLI_DIR="$REPO_ROOT/extensions/cli"
INSTALL_DIR="$PREFIX_DIR/local/lib/continue-continue-cli"
BIN_DIR="$PREFIX_DIR/local/bin"

fail() {
  printf '[blocked] %s\n' "$*" >&2
  exit 3
}

command -v node >/dev/null 2>&1 || fail "node is required on Vlad (Node >=18). Install Termux nodejs, then rerun."
command -v npm >/dev/null 2>&1 || fail "npm is required on Vlad. Install Termux nodejs/npm, then rerun."

NODE_MAJOR="$(node -p 'Number(process.versions.node.split(".")[0])')"
[ "$NODE_MAJOR" -ge 18 ] || fail "Continue CLI requires Node >=18; found $(node --version)."
[ -f "$CLI_DIR/package.json" ] || fail "run this script from the Continue Continue checkout; extensions/cli/package.json is missing"

printf '[cn-build] building exact fork on Vlad: %s\n' "$(git -C "$REPO_ROOT" rev-parse HEAD 2>/dev/null || printf unknown)"
printf '[cn-build] node=%s npm=%s\n' "$(node --version)" "$(npm --version)"

# The CLI build intentionally bundles its runtime into dist/index.js. Keep npm
# optional dependencies enabled: esbuild selects its platform package through
# that mechanism, including Android/arm64 where available.
export npm_config_audit=false
export npm_config_fund=false

(
  cd "$CLI_DIR"
  npm run build:local-deps
  npm run build
)

[ -x "$CLI_DIR/dist/cn.js" ] || fail "Continue build completed without executable dist/cn.js"
[ -s "$CLI_DIR/dist/index.js" ] || fail "Continue build completed without dist/index.js"

mkdir -p "$INSTALL_DIR" "$BIN_DIR"
rm -rf "$INSTALL_DIR/dist"
mkdir -p "$INSTALL_DIR/dist"
cp -a "$CLI_DIR/dist/." "$INSTALL_DIR/dist/"

cat > "$BIN_DIR/cn" <<EOF
#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
exec node "$INSTALL_DIR/dist/cn.js" "\$@"
EOF
chmod 0755 "$BIN_DIR/cn"

printf '[cn-install] binary=%s\n' "$BIN_DIR/cn"
printf '[cn-install] source_head=%s\n' "$(git -C "$REPO_ROOT" rev-parse HEAD 2>/dev/null || printf unknown)"
"$BIN_DIR/cn" --version
