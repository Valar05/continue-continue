import importlib.util
import json
import os
import pathlib
import stat
import tempfile
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).parent
SPEC = importlib.util.spec_from_file_location("adam_cli", ROOT / "adam_cli.py")
adam = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(adam)


class AdamCliTests(unittest.TestCase):
    def executable(self, root: pathlib.Path, name: str) -> str:
        path = root / name
        path.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        path.chmod(path.stat().st_mode | stat.S_IXUSR)
        return str(path)

    def test_code_routes_to_vlad_not_direct_model(self):
        with mock.patch.object(adam, "vlad", return_value=0) as invoke:
            rc = adam.main(["code", "fix", "the", "bootstrap"])
        self.assertEqual(rc, 0)
        invoke.assert_called_once_with(["code", "fix", "the", "bootstrap"])

    def test_unknown_command_blocks_without_model_fallback(self):
        with mock.patch.object(adam, "vlad") as invoke:
            rc = adam.main(["ponder"])
        self.assertEqual(rc, 3)
        invoke.assert_not_called()

    def test_shell_is_explicit_mechanical_lane(self):
        with mock.patch.object(adam, "shell_command", return_value=0) as shell:
            rc = adam.main(["shell", "git", "status"])
        self.assertEqual(rc, 0)
        shell.assert_called_once()
        self.assertEqual(shell.call_args.args[0], "git status")

    def test_cd_persists_across_invocations(self):
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            one = root / "one"
            two = root / "two"
            one.mkdir()
            two.mkdir()
            with mock.patch.dict(os.environ, {"ADAM_STATE_DIR": str(root / "state"), "ADAM_CWD": str(one)}, clear=False):
                self.assertEqual(adam.main(["cd", str(two)]), 0)
            with mock.patch.dict(os.environ, {"ADAM_STATE_DIR": str(root / "state")}, clear=False):
                self.assertEqual(adam.load_cwd(), two.resolve())

    def test_relative_cd_resolves_from_owned_cwd(self):
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            child = root / "child"
            child.mkdir()
            with mock.patch.dict(os.environ, {"ADAM_STATE_DIR": str(root / "state")}, clear=False):
                changed = adam.change_directory("child", root)
                self.assertEqual(changed, child.resolve())
                self.assertEqual(adam.load_cwd(), child.resolve())

    def test_shell_receipt_records_cwd_exit_and_no_model(self):
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            with mock.patch.dict(os.environ, {"ADAM_STATE_DIR": str(root / "state"), "ADAM_SHELL": "/bin/sh"}, clear=False):
                rc = adam.shell_command("pwd >/dev/null", root)
                self.assertEqual(rc, 0)
                receipt = json.loads(adam.shell_receipt_path().read_text(encoding="utf-8"))
            self.assertEqual(receipt["cwd"], str(root.resolve()))
            self.assertEqual(receipt["returncode"], 0)
            self.assertFalse(receipt["modelUsed"])


if __name__ == "__main__":
    unittest.main()
