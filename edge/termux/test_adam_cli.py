import importlib.util
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
        shell.assert_called_once_with("git status")


if __name__ == "__main__":
    unittest.main()
