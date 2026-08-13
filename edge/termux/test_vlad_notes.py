import json
import os
import pathlib
import tempfile
import unittest
from unittest import mock

import vlad_notes


class VladNotesTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.temp.name) / "project"
        self.state = pathlib.Path(self.temp.name) / "state"
        self.root.mkdir()
        (self.root / "AGENTS.md").write_text("NEXT ACTION: build the durable shell\nAPI_TOKEN=do-not-keep\n")
        (self.root / "secret-token.txt").write_text("forbidden")
        (self.root / "docs").mkdir()
        (self.root / "docs" / "status.md").write_text("Remaining Gate: phone receipt\n")
        self.env = mock.patch.dict(
            os.environ,
            {"VLAD_NOTES_STATE_DIR": str(self.state), "VLAD_NOTES_ROOT": str(self.root)},
            clear=False,
        )
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.temp.cleanup()

    def test_compile_query_next_and_receipt_are_deterministic(self):
        compiled = vlad_notes.compile_pack(None)
        self.assertEqual(2, compiled["sourceCount"])
        pack = json.loads(vlad_notes.pack_path().read_text())
        self.assertNotIn("do-not-keep", json.dumps(pack))
        self.assertNotIn("secret-token.txt", json.dumps(pack))

        queried = vlad_notes.query(["durable", "shell"])
        self.assertEqual("AGENTS.md", queried["matches"][0]["path"])

        selected = vlad_notes.next_action()["selected"]
        self.assertEqual("AGENTS.md", selected["path"])

        first = vlad_notes.append_receipt("ROUTE", ["AGENTS.md"])
        second = vlad_notes.append_receipt("PARK", ["docs/status.md"])
        self.assertEqual(first["receiptSha256"], second["previousReceiptSha256"])

    def test_same_idempotent_pack_bytes_have_verifiable_sidecar(self):
        with mock.patch("vlad_notes.time.time", return_value=1000):
            first = vlad_notes.compile_pack(None)
        first_bytes = vlad_notes.pack_path().read_bytes()
        with mock.patch("vlad_notes.time.time", return_value=2000):
            second = vlad_notes.compile_pack(None)
        self.assertEqual(first["packSha256"], second["packSha256"])
        self.assertEqual(first_bytes, vlad_notes.pack_path().read_bytes())
        status = vlad_notes.status()
        self.assertTrue(status["ready"])
        vlad_notes.pack_path().write_text("{}")
        self.assertFalse(vlad_notes.status()["ready"])


if __name__ == "__main__":
    unittest.main()
