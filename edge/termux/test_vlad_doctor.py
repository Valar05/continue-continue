import os
import pathlib
import stat
import tempfile
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

from vlad_doctor import diagnose


class OkHandler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b"{}")

    def log_message(self, *_args):
        return


class VladDoctorTests(unittest.TestCase):
    def executable(self, root: pathlib.Path, name: str) -> str:
        path = root / name
        path.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        path.chmod(path.stat().st_mode | stat.S_IXUSR)
        return str(path)

    def base_env(self, root: pathlib.Path) -> dict[str, str]:
        bin_dir = root / "bin"
        bin_dir.mkdir()
        edge = self.executable(bin_dir, "continue-continue-vlad")
        phone = self.executable(bin_dir, "home-center-phone-ask")
        for name in ("git", "python3", "ffmpeg", "ffprobe", "rg"):
            self.executable(bin_dir, name)
        return {
            "CONTINUE_CONTINUE_EDGE_DIR": str(root / "state"),
            "VLAD_EDGE_BIN": edge,
            "PHONE_ASK_BIN": phone,
            "VLAD_ALLOW_PHONE_HANDS": "1",
            "PATH": str(bin_dir),
        }

    def test_phone_hands_required_and_ready(self):
        with tempfile.TemporaryDirectory() as temp:
            env = self.base_env(pathlib.Path(temp))
            report = diagnose(env, {"phone_hands"})
            self.assertTrue(report["ready"])
            self.assertEqual(report["requiredFailures"], [])

    def test_permission_gate_blocks_phone_readiness(self):
        with tempfile.TemporaryDirectory() as temp:
            env = self.base_env(pathlib.Path(temp))
            env["VLAD_ALLOW_PHONE_HANDS"] = "0"
            report = diagnose(env, {"phone_hands"})
            self.assertFalse(report["ready"])
            self.assertIn("phone_hands_permission", report["requiredFailures"])

    def test_upstream_and_qwen_can_be_required(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), OkHandler)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory() as temp:
                env = self.base_env(pathlib.Path(temp))
                base = f"http://127.0.0.1:{server.server_address[1]}"
                env["CONTINUE_CONTINUE_UPSTREAM_URL"] = base
                env["QWEN_BASE_URL"] = base
                report = diagnose(env, {"upstream", "qwen"})
                self.assertTrue(report["ready"])
        finally:
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    unittest.main()
