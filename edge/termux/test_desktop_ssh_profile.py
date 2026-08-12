import importlib.util
import pathlib
import tempfile
import unittest

ROOT = pathlib.Path(__file__).parent
SPEC = importlib.util.spec_from_file_location("desktop_ssh", ROOT / "install_desktop_ssh_profile.py")
ssh_profile = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(ssh_profile)


class DesktopSshProfileTests(unittest.TestCase):
    def test_installs_standard_ssh_alias_without_secrets(self):
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp) / ".ssh"
            receipt = ssh_profile.install("desktop", "THECAULDRON", user="drew", port=2222, identity="~/.ssh/id_ed25519", env={"ADAM_SSH_DIR": str(root)})
            text = pathlib.Path(receipt["profile"]).read_text(encoding="utf-8")
            config = (root / "config").read_text(encoding="utf-8")
        self.assertIn("Host desktop", text)
        self.assertIn("HostName THECAULDRON", text)
        self.assertIn("User drew", text)
        self.assertIn("Port 2222", text)
        self.assertIn('IdentityFile "', text)
        self.assertIn("Include config.d/*", config)
        self.assertFalse(receipt["secretsStored"])
        self.assertEqual(receipt["command"], "ssh desktop")

    def test_reinstall_does_not_duplicate_include(self):
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp) / ".ssh"
            env = {"ADAM_SSH_DIR": str(root)}
            ssh_profile.install("desktop", "THECAULDRON", env=env)
            ssh_profile.install("desktop", "THECAULDRON", env=env)
            config = (root / "config").read_text(encoding="utf-8")
        self.assertEqual(config.count("Include config.d/*"), 1)

    def test_alias_validation_blocks_config_injection(self):
        with self.assertRaises(ValueError): ssh_profile.render_profile("desktop\nHost evil", "THECAULDRON")

    def test_host_validation_blocks_whitespace_injection(self):
        with self.assertRaises(ValueError): ssh_profile.render_profile("desktop", "host name")

    def test_user_validation_blocks_config_injection(self):
        with self.assertRaises(ValueError): ssh_profile.render_profile("desktop", "THECAULDRON", user="drew\nProxyCommand evil")

    def test_identity_validation_blocks_config_injection(self):
        with self.assertRaises(ValueError): ssh_profile.render_profile("desktop", "THECAULDRON", identity="~/.ssh/key\nProxyCommand evil")


if __name__ == "__main__": unittest.main()
