import importlib.util
import json
import pathlib
import stat
import sys
import tempfile
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

MODULE_PATH = pathlib.Path(__file__).with_name("vlad_doctor.py")
spec = importlib.util.spec_from_file_location("vlad_doctor", MODULE_PATH)
doctor = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = doctor
spec.loader.exec_module(doctor)


class OkHandler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        if self.path == "/api/tags":
            self.wfile.write(
                json.dumps(
                    {"models": [{"name": "qwen2.5-coder:1.5b", "size": 1500}]}
                ).encode("utf-8")
            )
        else:
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
        for name in ("cn", "git", "python3", "ffmpeg", "ffprobe", "rg"):
            self.executable(bin_dir, name)
        return {
            "CONTINUE_CONTINUE_EDGE_DIR": str(root / "state"),
            "CONTINUE_GLOBAL_DIR": str(root / "continue"),
            "VLAD_EDGE_BIN": edge,
            "VLAD_EDGE_INTERNAL": internal,
            "VLAD_ROUTING_SHEET": self.routing_sheet(root),
            "PHONE_ASK_BIN": phone,
            "VLAD_ALLOW_PHONE_HANDS": "1",
            "VLAD_ALLOW_LOCAL_EXEC": "0",
            "PATH": str(bin_dir),
        }

    def configure_continue(self, env: dict[str, str], base: str) -> None:
        env["VLAD_OLLAMA_URL"] = base
        root = pathlib.Path(env["CONTINUE_GLOBAL_DIR"])
        root.mkdir(parents=True, exist_ok=True)
        (root / "config.yaml").write_text(
            'name: Vlad Local\nversion: "1.0.0"\nschema: "v1"\nmodels:\n'
            '  - name: "Vlad qwen2.5-coder:1.5b"\n'
            "    provider: ollama\n"
            '    model: "qwen2.5-coder:1.5b"\n'
            "    roles:\n      - chat\n      - edit\n      - apply\n",
            encoding="utf-8",
        )

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

    def test_continue_required_and_ready(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), OkHandler)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory() as temp:
                env = self.base_env(pathlib.Path(temp))
                env["VLAD_ALLOW_LOCAL_EXEC"] = "1"
                self.configure_continue(
                    env, f"http://127.0.0.1:{server.server_address[1]}"
                )
                report = doctor.diagnose(env, {"continue"})
                self.assertTrue(report["ready"])
                self.assertEqual(report["requiredFailures"], [])
        finally:
            server.shutdown()
            server.server_close()

    def test_continue_requires_local_exec_permission(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), OkHandler)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory() as temp:
                env = self.base_env(pathlib.Path(temp))
                self.configure_continue(
                    env, f"http://127.0.0.1:{server.server_address[1]}"
                )
                report = doctor.diagnose(env, {"continue"})
                self.assertFalse(report["ready"])
                self.assertIn("continue_permission", report["requiredFailures"])
        finally:
            server.shutdown()
            server.server_close()

    def test_continue_respects_global_binary_policy(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), OkHandler)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory() as temp:
                env = self.base_env(pathlib.Path(temp))
                env["VLAD_ALLOW_LOCAL_EXEC"] = "1"
                env["VLAD_ALLOWED_BINS"] = "git,python3"
                self.configure_continue(
                    env, f"http://127.0.0.1:{server.server_address[1]}"
                )
                report = doctor.diagnose(env, {"continue"})
                self.assertFalse(report["ready"])
                self.assertIn("continue_policy", report["requiredFailures"])
        finally:
            server.shutdown()
            server.server_close()

    def test_continue_requires_reachable_ollama_and_matching_config(self):
        with tempfile.TemporaryDirectory() as temp:
            env = self.base_env(pathlib.Path(temp))
            env["VLAD_ALLOW_LOCAL_EXEC"] = "1"
            env["VLAD_OLLAMA_URL"] = "http://127.0.0.1:9"
            report = doctor.diagnose(env, {"continue"})
            self.assertFalse(report["ready"])
            self.assertIn("ollama", report["requiredFailures"])
            self.assertIn("continue_local_config", report["requiredFailures"])

    def test_continue_rejects_configured_model_not_installed(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), OkHandler)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory() as temp:
                env = self.base_env(pathlib.Path(temp))
                env["VLAD_ALLOW_LOCAL_EXEC"] = "1"
                base = f"http://127.0.0.1:{server.server_address[1]}"
                self.configure_continue(env, base)
                path = pathlib.Path(env["CONTINUE_GLOBAL_DIR"]) / "config.yaml"
                path.write_text(
                    path.read_text(encoding="utf-8").replace(
                        "qwen2.5-coder:1.5b", "missing-model:latest"
                    ),
                    encoding="utf-8",
                )
                report = doctor.diagnose(env, {"continue"})
                self.assertFalse(report["ready"])
                self.assertIn("continue_local_config", report["requiredFailures"])
        finally:
            server.shutdown()
            server.server_close()

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
