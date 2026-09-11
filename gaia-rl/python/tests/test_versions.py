import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from gaia_rl import versions


class VersionTests(unittest.TestCase):
    def test_changed_deleted_added_sources(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "gaia-engine/src/lib.rs"
            source.parent.mkdir(parents=True)
            source.write_bytes(b"original")
            manifest = hashlib.sha256(b"original").hexdigest() + "  gaia-engine/src/lib.rs\n"
            with patch.object(versions, "SOURCE_MANIFEST", manifest):
                versions.require_current_sources(root)
                source.write_bytes(b"changed")
                with self.assertRaises(versions.VersionMismatchError):
                    versions.require_current_sources(root)
                source.unlink()
                self.assertEqual(versions.source_differences(root), ["gaia-engine/src/lib.rs"])
                source.write_bytes(b"original")
                (source.parent / "new.rs").write_text("new")
                self.assertEqual(versions.source_differences(root), ["gaia-engine/src/new.rs"])

    def test_checkpoint_mismatch_fails_closed(self):
        saved = versions.runtime_versions()
        versions.require_compatible_versions(saved)
        for key in saved:
            with self.subTest(key=key):
                with self.assertRaises(versions.VersionMismatchError):
                    versions.require_compatible_versions({**saved, key: "different"})
        with self.assertRaises(versions.VersionMismatchError):
            versions.require_compatible_versions({})


if __name__ == "__main__":
    unittest.main()
