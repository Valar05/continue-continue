import importlib.util
import os
import pathlib
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).parent
MODULE = ROOT / "vlad_cli.py"
spec = importlib.util.spec_from_file_location("vlad_cli", MODULE)
vlad = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(vlad)


class VladCliTests(unittest.TestCase):
    def test_phone_shortcut_is_explicit_but_does_not_grant_permission(self):
        task = vlad.explicit_phone_task("Go home")
        self.assertEqual(task["domain"], "system")
        self.assertEqual(task["context"]["edge"]["action"]["kind"], "phone_hands")
        self.assertNotIn("VLAD_ALLOW_PHONE_HANDS", str(task))

    def test_continue_default_preserves_continue_as_requested_coding_organ(self):
        task = vlad.continue_task("Add one focused test")
        action = task["context"]["edge"]["action"]
        argv = action["argv"]
        self.assertEqual(argv[:2], ["cn", "-p"])
        self.assertEqual(action["allowedBins"], ["cn"])
        self.assertNotIn("--auto", argv)
        self.assertNotIn("--readonly", argv)
        self.assertTrue(any("Continue is the requested coding organ" in item for item in task["constraints"]))
        self.assertTrue(any("narrows shell authority" in item for item in task["constraints"]))

    def test_continue_custom_path_narrows_to_binary_basename(self):
        with mock.patch.dict(os.environ, {"VLAD_CN_BIN": "/opt/continue/bin/cn"}):
            task = vlad.continue_task("Add one focused test")
        action = task["context"]["edge"]["action"]
        self.assertEqual(action["argv"][0], "/opt/continue/bin/cn")
        self.assertEqual(action["allowedBins"], ["cn"])

    def test_review_is_readonly(self):
        task = vlad.continue_task("Review the diff", readonly=True)
        argv = task["context"]["edge"]["action"]["argv"]
        self.assertIn("--readonly", argv)
        self.assertNotIn("--auto", argv)

    def test_auto_is_explicit(self):
        task = vlad.continue_task("Implement the bounded task", auto=True)
        self.assertIn("--auto", task["context"]["edge"]["action"]["argv"])

    def test_continue_rejects_conflicting_modes(self):
        with self.assertRaises(ValueError):
            vlad.continue_task("bad", readonly=True, auto=True)

    def test_human_render_keeps_status_and_evidence(self):
        text = vlad.render_human(
            {
                "routing": {"route": "phone_hands"},
                "receipt": {
                    "status": "blocked",
                    "resultSummary": "Phone Hands permission is disabled.",
                    "evidence": ["gate:VLAD_ALLOW_PHONE_HANDS=0"],
                },
            }
        )
        self.assertIn("[blocked] route=phone_hands", text)
        self.assertIn("gate:VLAD_ALLOW_PHONE_HANDS=0", text)


if __name__ == "__main__":
    unittest.main()
