"""The manifest must describe the plugin that actually loads.

See tests/registration_probe.py for why this runs out-of-process from a temporary
directory rather than importing the package here.
"""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / "tests" / "registration_probe.py"


def run_probe(repo: Path):
    """Run the probe against `repo` from a clean cwd, home and environment."""
    with tempfile.TemporaryDirectory() as tmp:
        home = Path(tmp) / "home"
        home.mkdir()
        env = {k: v for k, v in os.environ.items()
               if not k.startswith(("HERMES_", "EMAIL_", "PYTHON"))}
        env.update(HOME=str(home), USERPROFILE=str(home), LOCALAPPDATA=str(home),
                   PYTHONUTF8="1")
        return subprocess.run([sys.executable, "-B", str(PROBE), str(repo), str(home)],
                              cwd=tmp, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)


class Registration(unittest.TestCase):
    def test_legacy_settings_feed_runtime_and_fabric_settings_win(self):
        import importlib.util
        import support

        package_name = "_registration_test_fabric"

        def clear_package():
            for name in tuple(sys.modules):
                if name == package_name or name.startswith(package_name + "."):
                    del sys.modules[name]

        clear_package()
        self.addCleanup(clear_package)
        spec = importlib.util.spec_from_file_location(
            package_name, ROOT / "__init__.py", submodule_search_locations=[str(ROOT)]
        )
        assert spec is not None and spec.loader is not None
        plugin = importlib.util.module_from_spec(spec)
        sys.modules[package_name] = plugin
        spec.loader.exec_module(plugin)
        companion = importlib.import_module(f"{package_name}.companion")
        forge_module = importlib.import_module(f"{package_name}.forge")
        tools_module = importlib.import_module(f"{package_name}.tools")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / ".hermes"
            profile = root / "profiles" / "quill"
            profile.mkdir(parents=True)
            with (profile / "config.yaml").open("w", encoding="utf-8") as f:
                support.yaml.safe_dump({"plugins": {"entries": {
                    "bot-forge": {"settings": {"allow_delete": True, "EMAIL_PASSWORD": "must-not-read"}},
                    "fabric": {"settings": {"allow_delete": False}}}}}, f)

            class Context:
                def __init__(self): self.handlers = {}
                def get_config(self, key, default=None): return None
                def register_tool(self, **kw): self.handlers[kw["name"]] = kw["handler"]
                def register_hook(self, *args): pass
                def register_skill(self, *args): pass
                def register_cli_command(self, **kw): pass

            ctx = Context()
            with mock.patch.dict(os.environ, {"HERMES_PROFILE": "quill"}), \
                 mock.patch.object(forge_module, "default_root", return_value=root), \
                 mock.patch.object(companion, "adopt_all"), \
                 mock.patch.object(companion, "companion_running", return_value=True), \
                 mock.patch.object(tools_module, "create_agent", return_value={"ok": True}) as create:
                plugin.register(ctx)
                ctx.handlers["create_agent"]({})
            settings = create.call_args.kwargs["settings"]
            self.assertFalse(settings["allow_delete"])
            self.assertNotIn("EMAIL_PASSWORD", settings)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / ".hermes"
            profile = root / "profiles" / "quill"
            profile.mkdir(parents=True)
            with (profile / "config.yaml").open("w", encoding="utf-8") as f:
                support.yaml.safe_dump({"plugins": {"entries": {
                    "bot-forge": {"settings": {"allow_delete": True}}}}}, f)
            with mock.patch.dict(os.environ, {"HERMES_PROFILE": "quill"}), \
                 mock.patch.object(forge_module, "default_root", return_value=root), \
                 mock.patch.object(companion, "adopt_all"), \
                 mock.patch.object(companion, "companion_running", return_value=True), \
                 mock.patch.object(tools_module, "create_agent", return_value={"ok": True}) as create:
                ctx = Context()
                plugin.register(ctx)
                ctx.handlers["create_agent"]({})
                self.assertTrue(create.call_args.kwargs["settings"]["allow_delete"])

    def test_manifest_matches_what_register_actually_registers(self):
        proc = run_probe(ROOT)
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        self.assertIn("CLI command", proc.stdout)
        self.assertNotIn("bot-forge-doctor", proc.stdout)

    def test_the_probe_notices_a_tool_that_stops_registering(self):
        """Guard the guard: a check that cannot fail is worse than no check.

        The copy is edited, never the checkout — dropping a tool from the real
        plugin.yaml would leave the repo broken if the assertion raised.
        """
        with tempfile.TemporaryDirectory() as tmp:
            copy = Path(tmp) / "bot_forge"
            _copy_tree(ROOT, copy)
            manifest = copy / "plugin.yaml"
            text = manifest.read_text(encoding="utf-8")
            self.assertIn("  - list_agents\n", text)
            manifest.write_text(text.replace("  - list_agents\n", "", 1), encoding="utf-8")
            proc = run_probe(copy)
        self.assertNotEqual(proc.returncode, 0,
                            "the probe passed a manifest that no longer declares list_agents")
        self.assertIn("list_agents", proc.stderr)


def _copy_tree(src: Path, dest: Path):
    """Copy the plugin, skipping everything that is not shipped."""
    import shutil
    shutil.copytree(
        src, dest,
        ignore=shutil.ignore_patterns(".git", "__pycache__", "videos", "docs", "*.png"))


if __name__ == "__main__":
    unittest.main()
