from hashlib import sha256
import importlib.util
import json
import re
from pathlib import Path
import tempfile
import tomllib
import unittest
from unittest.mock import patch


spec = importlib.util.spec_from_file_location("engine_kit_export", Path(__file__).with_name("export.py"))
exporter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(exporter)


class ExportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / "source"
        self.root.mkdir()
        for name in exporter.FILES:
            self.write(name, b"source\n")
        for directory, suffix in exporter.TREES.items():
            self.write(f"{directory}/sample{suffix}", b"unchanged\n")
        self.write("gaia-rl/pyproject.toml", b'''[build-system]
requires = ["maturin>=1,<2"]
build-backend = "maturin"
[project]
name = "gaia-rl"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = ["numpy==1.0"]
''')

    def write(self, name: str, data: bytes):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return path

    def test_allowlist_hashes_and_no_source_edits(self):
        for name in (".env", ".git/config", "gaia-rl/runs/model.pkl", "gaia-engine/.omc/private.json",
                     "gaia-engine/src/.private.rs", "gaia-engine/src/password.txt",
                     "gaia-frontend/src/assets/image.png", "gaia-rl/python/gaia_rl/_native.so",
                     "gaia-rl/python/gaia_rl/training.py"):
            self.write(name, b"private sentinel")
        before = {str(p): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        out = self.base / "kit"
        manifest = exporter.export(self.root, out)
        actual = {p.relative_to(out).as_posix() for p in out.rglob("*") if p.is_file()}
        self.assertEqual(actual, set(manifest["files"]) | {"MANIFEST.json"})
        for name, digest in manifest["files"].items():
            data = (out / name).read_bytes()
            self.assertEqual(sha256(data).hexdigest(), digest)
            self.assertNotIn(b"private sentinel", data)
        self.assertEqual(before, {str(p): p.read_bytes() for p in self.root.rglob("*") if p.is_file()})
        self.assertFalse(manifest["release_ready"])
        self.assertEqual(json.loads((out / "MANIFEST.json").read_text()), manifest)

    def test_minimal_package_keeps_versions_as_optional_extra(self):
        result = tomllib.loads(exporter.package_metadata(self.root).decode())
        self.assertEqual(result["project"]["dependencies"], [])
        self.assertEqual(result["project"]["optional-dependencies"], {"aec": ["numpy==1.0"]})
        self.assertEqual(result["project"]["requires-python"], ">=3.12")

    def test_deterministic_export(self):
        self.assertEqual(exporter.export(self.root, self.base / "one"),
                         exporter.export(self.root, self.base / "two"))

    def test_viewer_requires_explicit_opt_in(self):
        additions = {"VIEWER.md": b"private viewer", "gaia-frontend/src/assets/planets/gaia.png": b"image"}
        with patch.object(exporter, 'viewer_payload', return_value=additions) as viewer:
            plain = exporter.export(self.root, self.base / 'plain')
            viewer.assert_not_called()
            self.assertNotIn('VIEWER.md', plain['files'])
            bundled = exporter.export(self.root, self.base / 'viewer', with_viewer=True)
            viewer.assert_called_once()
            self.assertEqual(bundled['scope'], 'engine-python-and-private-viewer')
            self.assertIn('VIEWER.md', bundled['files'])
            self.assertFalse(bundled['release_ready'])
            self.assertEqual(plain['files']['gaia-rl/src/sample.rs'], bundled['files']['gaia-rl/src/sample.rs'])

    def test_real_viewer_includes_direct_asset_imports_without_private_state(self):
        files = exporter.viewer_payload(exporter.ROOT, exporter.TEMPLATES)
        self.assertIn('gaia-frontend/src/data/income.json', files)
        self.assertFalse(any('/.om' in name or '/node_modules/' in name for name in files))
        for name, data in files.items():
            if not name.endswith(('.ts', '.tsx', '.css')) or '/tests/' in name:
                continue
            for asset in re.findall(r'''['"]([^'"\n]+\.(?:png|jpg|jpeg|webp|svg))['"]''', data.decode()):
                source = (exporter.ROOT / name).parent / asset
                if source.is_file():
                    relative = source.resolve().relative_to(exporter.ROOT).as_posix()
                    self.assertIn(relative, files)

    def test_existing_output_is_never_overwritten(self):
        out = self.base / "existing"
        out.mkdir()
        (out / "keep").write_text("keep")
        with self.assertRaises(FileExistsError):
            exporter.export(self.root, out)
        self.assertEqual(list(out.iterdir()), [out / "keep"])

    def test_output_inside_source_rejected(self):
        with self.assertRaises(ValueError):
            exporter.export(self.root, self.root / "nested")
        self.assertFalse((self.root / "nested").exists())

    def test_missing_required_source_leaves_no_output(self):
        (self.root / exporter.FILES[0]).unlink()
        with self.assertRaises(ValueError):
            exporter.export(self.root, self.base / "kit")
        self.assertFalse((self.base / "kit").exists())

    def test_source_and_destination_symlinks_rejected(self):
        outside = self.base / "secret"
        outside.write_text("private")
        link = self.root / "gaia-engine/src/leak.rs"
        link.symlink_to(outside)
        with self.assertRaises(ValueError):
            exporter.export(self.root, self.base / "kit")
        self.assertFalse((self.base / "kit").exists())
        link.unlink()
        output_link = self.base / "output-link"
        output_link.symlink_to(self.base / "not-created")
        with self.assertRaises(ValueError):
            exporter.export(self.root, output_link)


if __name__ == "__main__":
    unittest.main()
