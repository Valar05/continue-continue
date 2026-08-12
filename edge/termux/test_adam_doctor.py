import importlib.util
import json
import pathlib
import stat
import tempfile
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).parent
SPEC = importlib.util.spec_from_file_location("adam_doctor", ROOT / "adam_doctor.py")
doctor = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(doctor)


class AdamDoctorTests(unittest.TestCase):
    def executable(self, root: pathlib.Path, name: str, body: str = "exit 0") -> str:
        path = root / name
        path.write_text(f"#!/bin/sh\n{body}\n", encoding="utf-8")
        path.chmod(path.stat().st_mode | stat.S_IXUSR)
        return str(path)

    def test_ready_requires_real_adam_shell_and_vlad_receipt(self):
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            bin_dir = root / "bin"
            bin_dir.mkdir()
            self.executable(bin_dir, "sh")
            self.executable(bin_dir, "adam")
            payload = json.dumps({"ready": True, "requiredFailures": [], "checks": []})
            self.executable(bin_dir, "vlad", f"printf '%s\\n' '{payload}'")
            env = {
                "PATH": str(bin_dir),
                "ADAM_SHELL": "sh",
                "ADAM_BIN": "adam",
                "ADAM_VLAD_BIN": "vlad",
                "ADAM_STATE_DIR": str(root / "state"),
            }
            report = doctor.diagnose(env)
            self.assertTrue(report["ready"])
            self.assertEqual(report["ownership"]["vlad"][0], "Ollama")
            self.assertIn("optional adviser", report["ownership"]["venice"][0])
            self.assertTrue(pathlib.Path(report["receiptPath"]).is_file())

    def test_unparseable_vlad_receipt_is_unknown_not_pass(self):
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            bin_dir = root / "bin"
            bin_dir.mkdir()
            self.executable(bin_dir, "sh")
            self.executable(bin_dir, "adam")
            self.executable(bin_dir, "vlad", "printf 'garbage\\n'")
            env = {
                "PATH": str(bin_dir),
                "ADAM_SHELL": "sh",
                "ADAM_BIN": "adam",
                "ADAM_VLAD_BIN": "vlad",
                "ADAM_STATE_DIR": str(root / "state"),
            }
            report = doctor.diagnose(env)
            check = next(item for item in report["checks"] if item["name"] == "vlad_continue")
            self.assertEqual(check["state"], "UNKNOWN")
            self.assertFalse(report["ready"])

    def test_adam_never_probes_ollama_directly(self):
        source = (ROOT / "adam_doctor.py").read_text(encoding="utf-8")
        self.assertNotIn("/api/tags", source)
        self.assertNotIn("urllib", source)


if __name__ == "__main__":
    unittest.main()
