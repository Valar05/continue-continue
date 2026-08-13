#!/usr/bin/env python3
import json
import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import codex_worker


FAKE = '''#!/usr/bin/env python3
import json, os, pathlib, sys
if sys.argv[1:3] == ["login", "status"]:
    print("Logged in using ChatGPT OAuth")
    raise SystemExit(0)
assert "OPENAI_API_KEY" not in os.environ
out = pathlib.Path(sys.argv[sys.argv.index("--output-last-message") + 1])
out.write_text("worker finished\\n", encoding="utf-8")
print(json.dumps({"type":"thread.started","thread_id":"thread-real-123"}))
print(json.dumps({"type":"turn.completed"}))
'''


class CodexWorkerContract(unittest.TestCase):
    def test_doctor_and_run_capture_real_thread(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            fake = root / "codex"
            fake.write_text(FAKE, encoding="utf-8")
            fake.chmod(fake.stat().st_mode | stat.S_IXUSR)
            state = root / "state"
            env = {
                "ADAM_CODEX_BIN": str(fake),
                "ADAM_CODEX_STATE_DIR": str(state),
                "OPENAI_API_KEY": "must-not-cross",
            }
            with mock.patch.dict(os.environ, env, clear=False):
                self.assertEqual(codex_worker.doctor(True), 0)
                self.assertEqual(codex_worker.invoke("bounded task", root), 0)
            receipt = json.loads((state / "latest.json").read_text(encoding="utf-8"))
            self.assertEqual(receipt["threadId"], "thread-real-123")
            self.assertEqual(receipt["state"], "COMPLETED_PRESERVED")
            self.assertTrue(receipt["auth"]["apiKeyEnvironmentRemoved"])

    def test_non_chatgpt_auth_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            fake = root / "codex"
            fake.write_text("#!/bin/sh\necho 'Logged in with API key'\n", encoding="utf-8")
            fake.chmod(fake.stat().st_mode | stat.S_IXUSR)
            with mock.patch.dict(os.environ, {"ADAM_CODEX_BIN": str(fake)}, clear=False):
                self.assertFalse(codex_worker.auth_status(str(fake))["ok"])


if __name__ == "__main__":
    unittest.main()
