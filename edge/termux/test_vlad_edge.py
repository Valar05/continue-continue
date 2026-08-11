import importlib.util
import json
import os
import pathlib
import tempfile
import unittest
from unittest import mock

MODULE_PATH = pathlib.Path(__file__).with_name("vlad_edge.py")
spec = importlib.util.spec_from_file_location("vlad_edge", MODULE_PATH)
vlad = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(vlad)


class VladEdgeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.env = mock.patch.dict(
            os.environ,
            {"CONTINUE_CONTINUE_EDGE_DIR": self.temp.name},
            clear=False,
        )
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.temp.cleanup()

    def task(self, **extra):
        return {
            "taskId": "vlad-test-001",
            "actor": "vlad",
            "domain": "system",
            "goal": "Open the phone home screen.",
            "acceptanceCriteria": ["Phone receipt exists"],
            **extra,
        }

    def test_preserves_open_domain_contract(self):
        task = vlad.normalize_task(
            {"taskId": "vlad-shader-001", "domain": "shader_bake", "goal": "Bake it"}
        )
        self.assertEqual(task["domain"], "shader_bake")
        self.assertEqual(task["actor"], "vlad")

    def test_phone_hands_intent_does_not_grant_permission(self):
        record = vlad.create_record(
            self.task(
                context={
                    "edge": {
                        "action": {"kind": "phone_hands", "prompt": "Go home."}
                    }
                }
            )
        )
        result = vlad.execute(record)
        self.assertEqual(result["status"], "blocked")
        self.assertIn("gate:VLAD_ALLOW_PHONE_HANDS=0", result["evidence"])

    def test_shell_intent_does_not_grant_permission(self):
        record = vlad.create_record(
            self.task(
                taskId="vlad-shell-001",
                context={"edge": {"action": {"kind": "shell", "argv": ["git", "status"]}}},
            )
        )
        result = vlad.execute(record)
        self.assertEqual(result["status"], "blocked")
        self.assertIn("gate:VLAD_ALLOW_LOCAL_EXEC=0", result["evidence"])

    def test_task_allowed_bins_cannot_enlarge_global_policy(self):
        with mock.patch.dict(
            os.environ,
            {"VLAD_ALLOW_LOCAL_EXEC": "1", "VLAD_ALLOWED_BINS": "git,python3"},
        ):
            record = vlad.create_record(
                self.task(
                    taskId="vlad-shell-narrow-001",
                    context={
                        "edge": {
                            "action": {
                                "kind": "shell",
                                "argv": ["cn", "-p", "review"],
                                "allowedBins": ["cn"],
                            }
                        }
                    },
                )
            )
            result = vlad.execute(record)
        self.assertEqual(result["status"], "blocked")
        self.assertIn("allowed_bins:", result["evidence"])

    def test_task_allowed_bins_can_narrow_broader_policy(self):
        with mock.patch.dict(
            os.environ,
            {"VLAD_ALLOW_LOCAL_EXEC": "1", "VLAD_ALLOWED_BINS": "cn,git"},
        ):
            record = vlad.create_record(
                self.task(
                    taskId="vlad-shell-narrow-002",
                    context={
                        "edge": {
                            "action": {
                                "kind": "shell",
                                "argv": ["git", "status"],
                                "allowedBins": ["cn"],
                            }
                        }
                    },
                )
            )
            result = vlad.execute(record)
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["evidence"], ["allowed_bins:cn"])

    def test_task_allowed_bins_executes_only_intersection(self):
        completed = mock.MagicMock(returncode=0, stdout="reviewed", stderr="")
        with mock.patch.dict(
            os.environ,
            {"VLAD_ALLOW_LOCAL_EXEC": "1", "VLAD_ALLOWED_BINS": "cn,git"},
        ), mock.patch("subprocess.run", return_value=completed) as run:
            record = vlad.create_record(
                self.task(
                    taskId="vlad-shell-narrow-003",
                    context={
                        "edge": {
                            "action": {
                                "kind": "shell",
                                "argv": ["cn", "-p", "--readonly", "review"],
                                "allowedBins": ["cn"],
                            }
                        }
                    },
                )
            )
            result = vlad.execute(record)
        self.assertEqual(result["status"], "completed")
        self.assertIn("shell:allowed_bins=cn", result["evidence"])
        run.assert_called_once()

    def test_delegation_preserves_task_id_and_is_not_completion(self):
        response = {"queued": True, "task": {"taskId": "vlad-delegate-001"}}
        fake = mock.MagicMock()
        fake.__enter__.return_value = fake
        fake.__exit__.return_value = False
        fake.read.return_value = json.dumps(response).encode()
        with mock.patch.dict(
            os.environ,
            {"CONTINUE_CONTINUE_UPSTREAM_URL": "http://127.0.0.1:8000"},
        ), mock.patch("urllib.request.urlopen", return_value=fake):
            with mock.patch("json.load", return_value=response):
                record = vlad.create_record(
                    {
                        "taskId": "vlad-delegate-001",
                        "actor": "vlad",
                        "domain": "video",
                        "goal": "Render the heavy scene.",
                    }
                )
                result = vlad.execute(record)

        self.assertEqual(result["status"], "delegated")
        self.assertEqual(result["receipt"]["status"], "delegated")
        self.assertIn("upstream-task:vlad-delegate-001", result["evidence"])

    def test_without_safe_route_blocks_instead_of_substituting(self):
        with mock.patch.dict(
            os.environ,
            {
                "CONTINUE_CONTINUE_UPSTREAM_URL": "",
                "QWEN_BASE_URL": "",
            },
        ):
            record = vlad.create_record(
                {
                    "taskId": "vlad-no-route-001",
                    "actor": "vlad",
                    "domain": "image",
                    "goal": "Render a huge image.",
                }
            )
            result = vlad.execute(record)
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["evidence"], ["route:blocked"])


if __name__ == "__main__":
    unittest.main()
