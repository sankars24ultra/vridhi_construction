import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import unquote, urlsplit
import zipfile

SPEC = importlib.util.spec_from_file_location("bootstrap", Path(__file__).resolve().parents[1] / "bootstrap.py")
bootstrap = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bootstrap)


class BootstrapTests(unittest.TestCase):
    def test_supported_platforms(self):
        for system, machine, expected in [
            ("Darwin", "arm64", ("darwin", "arm64")),
            ("Darwin", "x86_64", ("darwin", "x64")),
            ("Windows", "AMD64", ("win", "x64")),
            ("Windows", "ARM64", ("win", "arm64")),
        ]:
            with self.subTest(system=system, machine=machine), patch.object(bootstrap.platform, "system", return_value=system), patch.object(bootstrap.platform, "machine", return_value=machine):
                self.assertEqual(bootstrap.supported_platform(), expected)

    def test_unsupported_platform_is_explicit(self):
        with patch.object(bootstrap.platform, "system", return_value="Linux"):
            with self.assertRaises(bootstrap.StartupError):
                bootstrap.supported_platform()

    def test_node_versions(self):
        for version, expected in [
            ("v22.12.0", True), ("v22.22.0", True), ("v24.0.0", True),
            ("v20.19.0", False), ("v22.11.0", False), ("v23.1.0", False),
            ("v26.0.0", False), ("invalid", False),
        ]:
            with self.subTest(version=version), patch.object(bootstrap.subprocess, "check_output", return_value=version):
                self.assertEqual(bootstrap.compatible_node("node"), expected)

    def test_missing_node_does_not_succeed(self):
        with patch.object(bootstrap.subprocess, "check_output", side_effect=FileNotFoundError):
            self.assertFalse(bootstrap.compatible_node("missing"))

    def test_npm_is_invoked_as_javascript_not_windows_cmd(self):
        with tempfile.TemporaryDirectory() as d:
            node = Path(d) / "node.exe"
            npm = Path(d) / "node_modules/npm/bin/npm-cli.js"
            npm.parent.mkdir(parents=True)
            npm.write_text("")
            self.assertEqual(bootstrap.npm_cli(node), npm)

    def test_existing_configuration_untouched(self):
        with tempfile.TemporaryDirectory() as d, patch.object(bootstrap, "ROOT", Path(d)), patch("builtins.input", side_effect=AssertionError("Must not prompt")):
            env = Path(d) / ".env"
            env.write_text("EXISTING=keep\n")
            bootstrap.ensure_config()
            self.assertEqual(env.read_text(), "EXISTING=keep\n")

    def test_config_encodes_credentials_without_printing_them(self):
        with tempfile.TemporaryDirectory() as d, patch.object(bootstrap, "ROOT", Path(d)), patch("builtins.input", side_effect=["127.0.0.1", "5434", "user@example", "test_database"]), patch.object(bootstrap.getpass, "getpass", return_value="p@ss:'$word"), contextlib.redirect_stdout(io.StringIO()) as output:
            bootstrap.ensure_config()
            content = (Path(d) / ".env").read_text()
            url = content.split("DATABASE_URL='")[1].split("'\n")[0]
            parsed = urlsplit(url)
            self.assertEqual(unquote(parsed.username), "user@example")
            self.assertEqual(unquote(parsed.password), "p@ss:'$word")
            self.assertEqual(parsed.port, 5434)
            self.assertEqual(parsed.path, "/test_database")
            self.assertNotIn("p@ss", output.getvalue())
            self.assertIn("SESSION_SECRET=", content)
            self.assertNotIn("DEMO_PASSWORD", content)

    def test_bad_port_does_not_write_config(self):
        with tempfile.TemporaryDirectory() as d, patch.object(bootstrap, "ROOT", Path(d)), patch("builtins.input", side_effect=["localhost", "99999"]):
            with self.assertRaises(bootstrap.StartupError):
                bootstrap.ensure_config()
            self.assertFalse((Path(d) / ".env").exists())

    def test_invalid_database_name_does_not_write_config(self):
        with tempfile.TemporaryDirectory() as d, patch.object(bootstrap, "ROOT", Path(d)), patch("builtins.input", side_effect=["localhost", "5432", "testuser", "name with spaces"]), patch.object(bootstrap.getpass, "getpass", return_value=""):
            with self.assertRaisesRegex(bootstrap.StartupError, "database name"):
                bootstrap.ensure_config()
            self.assertFalse((Path(d) / ".env").exists())

    def test_malformed_marker_fails_explicitly(self):
        with tempfile.TemporaryDirectory() as d:
            marker = Path(d) / "marker.json"
            marker.write_text("[]")
            with self.assertRaisesRegex(bootstrap.StartupError, "Invalid startup marker"):
                bootstrap.read_json(marker)

    def test_zip_traversal_rejected(self):
        for filename in ["../outside", "/absolute", "C:/outside", "..\\outside"]:
            with self.subTest(filename=filename), tempfile.TemporaryDirectory() as d:
                archive = Path(d) / "node.zip"
                with zipfile.ZipFile(archive, "w") as z:
                    z.writestr(filename, "unsafe")
                with self.assertRaises(bootstrap.StartupError):
                    bootstrap.extract_node(archive, Path(d) / "out")

    def test_tar_traversal_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            archive = Path(d) / "node.tar.gz"
            with tarfile.open(archive, "w:gz") as source:
                member = tarfile.TarInfo("../../outside")
                member.size = 1
                source.addfile(member, io.BytesIO(b"x"))
            with self.assertRaises(tarfile.FilterError):
                bootstrap.extract_node(archive, Path(d) / "out")

    def test_checksum_mismatch_rejects_runtime(self):
        def fake_fetch(url, destination):
            if url.endswith("SHASUMS256.txt"):
                destination.write_text("0" * 64 + "  node-v24.1.0-darwin-arm64.tar.gz\n")
            else:
                destination.write_bytes(b"bad archive")

        with tempfile.TemporaryDirectory() as d, patch.object(bootstrap, "TOOLS", Path(d)), patch.object(bootstrap, "supported_platform", return_value=("darwin", "arm64")), patch.object(bootstrap.shutil, "which", return_value=None), patch.object(bootstrap, "fetch", side_effect=fake_fetch):
            with self.assertRaisesRegex(bootstrap.StartupError, "checksum mismatch"):
                bootstrap.ensure_node()
            self.assertFalse((Path(d) / "node.json").exists())

    def test_frontend_unchanged_skips_installation(self):
        with tempfile.TemporaryDirectory() as d, patch.object(bootstrap, "FRONTEND", Path(d)), patch.object(bootstrap.subprocess, "check_output", return_value="v24.1.0"), patch.object(bootstrap, "run") as run:
            root = Path(d)
            for f in ["package.json", "package-lock.json"]:
                (root / f).write_text("{}")
            for f in ["node_modules/vite/bin/vite.js", "node_modules/typescript/bin/tsc"]:
                p = root / f
                p.parent.mkdir(parents=True)
                p.write_text("")
            marker = root / "node_modules/.vridhi-dependencies"
            expected = bootstrap.digest([root / "package.json", root / "package-lock.json"]) + "v24.1.0"
            marker.write_text(expected)
            bootstrap.ensure_frontend(Path("node"), Path("npm-cli.js"), {})
            run.assert_not_called()
            (root / "package-lock.json").write_text('{"changed":true}')
            bootstrap.ensure_frontend(Path("node"), Path("npm-cli.js"), {})
            self.assertEqual(run.call_args.args[0], ["node", "npm-cli.js", "ci", "--include=dev", "--no-audit", "--no-fund"])

    def test_failed_install_does_not_write_success_marker(self):
        with tempfile.TemporaryDirectory() as d, patch.object(bootstrap, "FRONTEND", Path(d)), patch.object(bootstrap.subprocess, "check_output", return_value="v24.1.0"), patch.object(bootstrap, "run", side_effect=bootstrap.StartupError("network")):
            root = Path(d)
            for f in ["package.json", "package-lock.json"]:
                (root / f).write_text("{}")
            with self.assertRaises(bootstrap.StartupError):
                bootstrap.ensure_frontend(Path("node"), Path("npm-cli.js"), {})
            self.assertFalse((root / "node_modules/.vridhi-dependencies").exists())

    def test_untracked_busy_port_not_reused_or_killed(self):
        with tempfile.TemporaryDirectory() as d, patch.object(bootstrap, "RUN", Path(d)), patch.object(bootstrap, "listening", return_value=True), patch.object(bootstrap.subprocess, "Popen") as popen:
            with self.assertRaisesRegex(bootstrap.StartupError, "untracked"):
                bootstrap.service("api", [8000], [], Path(d), {}, "hash")
            popen.assert_not_called()

    def test_healthy_owned_service_reused(self):
        with tempfile.TemporaryDirectory() as d, patch.object(bootstrap, "RUN", Path(d)), patch.object(bootstrap, "listening", return_value=True), patch.object(bootstrap, "healthy", return_value=True), patch.object(bootstrap.subprocess, "Popen") as popen:
            (Path(d) / "api.json").write_text(json.dumps({"root": str(bootstrap.ROOT), "port": 8000, "pid": 1234, "fingerprint": "same"}))
            self.assertEqual(bootstrap.service("api", [8000], [], Path(d), {}, "same"), 8000)
            popen.assert_not_called()

    def test_changed_code_requires_explicit_restart(self):
        with tempfile.TemporaryDirectory() as d, patch.object(bootstrap, "RUN", Path(d)), patch.object(bootstrap, "listening", return_value=True):
            (Path(d) / "api.json").write_text(json.dumps({"root": str(bootstrap.ROOT), "port": 8000, "pid": 1234, "fingerprint": "old"}))
            with self.assertRaisesRegex(bootstrap.StartupError, "1234"):
                bootstrap.service("api", [8000], [], Path(d), {}, "new")

    def test_command_failure_surfaces(self):
        with patch.object(bootstrap.subprocess, "run", return_value=subprocess.CompletedProcess([], 1)):
            with self.assertRaises(bootstrap.StartupError):
                bootstrap.run(["python", "-m", "pip"])

    def test_lock_blocks_second_launcher(self):
        with tempfile.TemporaryDirectory() as d, patch.object(bootstrap, "RUN", Path(d)):
            with bootstrap.startup_lock():
                with self.assertRaises(bootstrap.StartupError):
                    with bootstrap.startup_lock():
                        self.fail("Second launcher obtained the same lock")


if __name__ == "__main__":
    unittest.main()
