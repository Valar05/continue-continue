import importlib.util
import os
import pathlib
import tempfile
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).parent


def load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / filename)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


router = load_module("vlad_router", "vlad_router.py")
edge = load_module("vlad_edge_for_router_test", "vlad_edge.py")


class VladRouterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.env = mock.patch.dict(
            os.environ,
            {
                "CONTINUE_CONTINUE_EDGE_DIR": self.temp.name,
                "VLAD_ALLOW_PHONE_HANDS": "0",
                "VLAD_ALLOW_LOCAL_EXEC": "0",
            },
            clear=False,
        )
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.temp.cleanup()

    def sheet(self, text: str) -> pathlib.Path:
        path = pathlib.Path(self.temp.name) / "routes.csv"
        path.write_text(text, encoding="utf-8")
        return path

    def test_raw_request_is_classified_before_edge(self):
        sheet = self.sheet(
            "priority,enabled,name,domain,contains_any,contains_all,route,target_domain,command,phone_prompt,reason\n"
            "10,1,video,*,video,,delegate,video,,,heavy media\n"
        )
        task, decision = router.apply_sheet({"request": "Render a short video"}, sheet)
        self.assertEqual(task["domain"], "video")
        self.assertEqual(decision["route"], "delegate")
        self.assertEqual(task["context"]["edge"]["action"], {"kind": "delegate"})

    def test_first_match_wins(self):
        sheet = self.sheet(
            "priority,enabled,name,domain,contains_any,contains_all,route,target_domain,command,phone_prompt,reason\n"
            "20,1,later,*,settings,,delegate,system,,,later\n"
            "10,1,first,*,settings,,phone_hands,system,,{goal},first\n"
        )
        _, decision = router.apply_sheet({"request": "Open settings"}, sheet)
        self.assertEqual(decision["rule"], "first")
        self.assertEqual(decision["route"], "phone_hands")

    def test_explicit_action_is_never_overridden(self):
        sheet = self.sheet(
            "priority,enabled,name,domain,contains_any,contains_all,route,target_domain,command,phone_prompt,reason\n"
            "1,1,block,*,settings,,blocked,system,,,block\n"
        )
        payload = {
            "domain": "system",
            "goal": "Open settings",
            "context": {"edge": {"action": {"kind": "delegate"}}},
        }
        task, decision = router.apply_sheet(payload, sheet)
        self.assertEqual(decision["route"], "explicit")
        self.assertEqual(task["context"]["edge"]["action"], {"kind": "delegate"})

    def test_sheet_route_does_not_grant_phone_hands_permission(self):
        sheet = self.sheet(
            "priority,enabled,name,domain,contains_any,contains_all,route,target_domain,command,phone_prompt,reason\n"
            "10,1,phone,*,home screen,,phone_hands,system,,{goal},phone\n"
        )
        routed, decision = router.apply_sheet({"request": "Go to the home screen"}, sheet)
        self.assertEqual(decision["route"], "phone_hands")
        record = edge.create_record(routed)
        result = edge.execute(record)
        self.assertEqual(result["status"], "blocked")
        self.assertIn("gate:VLAD_ALLOW_PHONE_HANDS=0", result["evidence"])

    def test_no_match_falls_through_without_fabricating_action(self):
        sheet = self.sheet(
            "priority,enabled,name,domain,contains_any,contains_all,route,target_domain,command,phone_prompt,reason\n"
            "10,1,phone,*,home screen,,phone_hands,system,,{goal},phone\n"
        )
        task, decision = router.apply_sheet({"request": "Something novel"}, sheet)
        self.assertFalse(decision["matched"])
        self.assertEqual(decision["route"], "passthrough")
        self.assertNotIn("edge", task["context"])


if __name__ == "__main__":
    unittest.main()
