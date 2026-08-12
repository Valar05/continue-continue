#!/usr/bin/env python3
import pathlib
import subprocess
import sys

root = pathlib.Path(__file__).parent
subprocess.run([sys.executable, str(root / "test_desktop_ssh_profile.py")], check=True)
install = (root / "install.sh").read_text(encoding="utf-8")
assert 'install_desktop_ssh_profile.py" "$BIN_DIR/adam-ssh-profile"' in install
assert "ssh desktop" in install
print("desktop SSH integration gate: PASS")
