import importlib.util
import pathlib
import stat
import tempfile
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

MODULE_PATH = pathlib.Path(__file__).with_name("vlad_doctor.py")
spec = importlib.util.spec_from_file_location("vlad_doctor", MODULE_PATH)
doctor = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(doctor)


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

    def routing_sheet(self, root: pathlib.Path) -> str:
        path = root / "routes.csv"
        path.write_text(
            "priority,enabled,name,domain,contains_any,contains_all,route,target_domain,command,phone_prompt,reason\n"
            "10,1,phone,*,settings,,phone_hands,system,,{goal},phone\n",
            encoding="utf-8",
        )
        return str(path)

    def base_env(self, root: pathlib.Path) -> dict[str, str]:
        bin_dir = root / "bin"
        bin_dir.mkdir()
        edge = self.executable(bin_dir, "continue-continue-vlad")
        internal = self.executable(bin_dir, "continue-continue-vlad-edge")
        phone = self.executable(bin_dir, "home-center-phone-ask")
        for name in ("git", "python3", "ffmpeg", "ffprobe", "rg"):
            self.executable(bin_dir, name)
        return {
            "CONTINUE_CONTINUE_EDGE_DIR": str(root / "state"),
            "VLAD_EDGE_BIN": edge,
            "VLAD_EDGE_INTERNAL": internal,
            "VLAD_ROUTING_SHEET": self.routing_sheet(root),
            "PHONE_ASK_BIN": phone,
            "VLAD_ALLOW_PHONE_HANDS": "1",
            "PATH": str(bin_dir),
        }

    def test_phone_hands_required_and_ready(self):
        with tempfile.TemporaryDirectory() as temp:
            env = self.base_env(pathlib.Path(temp))
            report = doctor.diagnose(env, {"phone_hands"})
            self.assertTrue(report["ready"])
            self.assertEqual(report["requiredFailures"], [])

    def test_permission_gate_blocks_phone_readiness(self):
        with tempfile.TemporaryDirectory() as temp:
            env = self.base_env(pathlib.Path(temp))
            env["VLAD_ALLOW_PHONE_HANDS"] = "0"
            report = doctor.diagnose(env, {"phone_hands"})
            self.assertFalse(report["ready"])
            self.assertIn("phone_hands_permission", report["requiredFailures"])

    def test_missing_routing_sheet_blocks_readiness(self):
        with tempfile.TemporaryDirectory() as temp:
            env = self.base_env(pathlib.Path(temp))
            env["VLAD_ROUTING_SHEET"] = str(pathlib.Path(temp) / "missing.csv")
            report = doctor.diagnose(env)
            self.assertFalse(report["ready"])
            self.assertIn("routing_sheet", report["requiredFailures"])

    def test_malformed_enabled_route_blocks_readiness(self):
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            env = self.base_env(root)
            sheet = pathlib.Path(env["VLAD_ROUTING_SHEET"])
            sheet.write_text(
                "priority,enabled,name,domain,contains_any,contains_all,route,target_domain,command,phone_prompt,reason\n"
                "banana,1,bad,*,settings,,teleport,system,,{goal},bad\n",
                encoding="utf-8",
            )
            report = doctor.diagnose(env)
            self.assertFalse(report["ready"])
            self.assertIn("routing_sheet", report["requiredFailures"])

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
                report = doctor.diagnose(env, {"upstream", "qwen"})
                self.assertTrue(report["ready"])
        finally:
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    unittest.main()
