import importlib.util
import json
import pathlib
import tempfile
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

MODULE_PATH = pathlib.Path(__file__).with_name("vlad_continue_bootstrap.py")
spec = importlib.util.spec_from_file_location("vlad_continue_bootstrap", MODULE_PATH)
bootstrap = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(bootstrap)


class OllamaHandler(BaseHTTPRequestHandler):
    models = [
        {"name": "llama3.2:3b", "size": 3000},
        {"name": "qwen2.5-coder:1.5b", "size": 1500},
        {"name": "qwen2.5-coder:7b", "size": 7000},
    ]

    def do_GET(self):  # noqa: N802
        if self.path != "/api/tags":
            self.send_response(404)
            self.end_headers()
            return
        body = json.dumps({"models": self.models}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args):
        return


class VladContinueBootstrapTests(unittest.TestCase):
    def setUp(self):
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), OllamaHandler)
        self.thread = Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()

    def test_prefers_smallest_qwen_coder(self):
        models = bootstrap.list_models({"VLAD_OLLAMA_URL": self.base})
        self.assertEqual(bootstrap.choose_model(models), "qwen2.5-coder:1.5b")

    def test_explicit_model_must_already_exist(self):
        models = bootstrap.list_models({"VLAD_OLLAMA_URL": self.base})
        with self.assertRaises(RuntimeError):
            bootstrap.choose_model(models, "not-installed:latest")

    def test_bootstrap_writes_minimal_continue_config(self):
        with tempfile.TemporaryDirectory() as temp:
            env = {
                "VLAD_OLLAMA_URL": self.base,
                "CONTINUE_GLOBAL_DIR": temp,
            }
            result = bootstrap.bootstrap(env)
            text = pathlib.Path(result["config"]).read_text(encoding="utf-8")
            self.assertEqual(result["model"], "qwen2.5-coder:1.5b")
            self.assertIn("provider: ollama", text)
            self.assertIn('model: "qwen2.5-coder:1.5b"', text)
            self.assertIn("- chat", text)
            self.assertIn("- edit", text)
            self.assertIn("- apply", text)
            self.assertNotIn("autocomplete", text)
            self.assertNotIn("embed", text)

    def test_default_empty_continue_config_is_replaceable(self):
        self.assertTrue(
            bootstrap.config_is_replaceable(
                'name: Main Config\nversion: "1.0.0"\nschema: "v1"\nmodels: []\n'
            )
        )

    def test_nonempty_user_config_requires_force_and_is_backed_up(self):
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            config = root / "config.yaml"
            config.write_text(
                'name: Mine\nversion: "1.0.0"\nschema: "v1"\nmodels:\n  - provider: anthropic\n    model: x\n',
                encoding="utf-8",
            )
            env = {"VLAD_OLLAMA_URL": self.base, "CONTINUE_GLOBAL_DIR": temp}
            with self.assertRaises(RuntimeError):
                bootstrap.bootstrap(env)
            result = bootstrap.bootstrap(env, force=True)
            self.assertIsNotNone(result["backup"])
            self.assertTrue(pathlib.Path(result["backup"]).is_file())
            self.assertIn("provider: ollama", config.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
