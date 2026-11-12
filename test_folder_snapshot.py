import contextlib
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from folder_snapshot import compare, main, read_manifest, snapshot


class SnapshotTests(unittest.TestCase):
    def setUp(self):
        workspace = TemporaryDirectory()
        self.addCleanup(workspace.cleanup)
        self.workspace = Path(workspace.name)
        self.root = self.workspace / "files"
        self.root.mkdir()

    def test_content_changes_even_at_same_size(self):
        changing = self.root / "notes.txt"
        changing.write_bytes(b"old")
        (self.root / "removed.txt").touch()
        old = snapshot(self.root)["files"]

        changing.write_bytes(b"new")
        (self.root / "removed.txt").unlink()
        (self.root / "added.txt").touch()
        new = snapshot(self.root)["files"]

        self.assertEqual(compare(old, new), {
            "added": ["added.txt"], "removed": ["removed.txt"], "changed": ["notes.txt"],
        })

    def test_relative_paths_and_excludes(self):
        for folder in ["excluded", "nested"]:
            (self.root / folder).mkdir()
            (self.root / folder / "file.txt").touch()
        (self.root / "nested" / "scratch.tmp").touch()
        files = snapshot(self.root, ["excluded", "*.tmp"])["files"]
        self.assertEqual(list(files), ["nested/file.txt"])

    def test_invalid_manifest_rejected(self):
        manifest = self.workspace / "invalid.json"
        manifest.write_text(json.dumps({"version": 1, "files": {
            "../escape.txt": {"bytes": 0, "sha256": "0" * 64},
        }}), encoding="utf-8")
        with self.assertRaises(ValueError):
            read_manifest(manifest)

    def test_create_is_deterministic_and_preserves_existing_output(self):
        (self.root / "file.txt").touch()
        left, right = self.workspace / "one.json", self.workspace / "two.json"
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main(["create", str(self.root), str(left)]), 0)
            self.assertEqual(main(["create", str(self.root), str(right)]), 0)
            self.assertEqual(main(["create", str(self.root), str(left)]), 2)
        self.assertEqual(left.read_bytes(), right.read_bytes())

    def test_diff_reports_changes_with_exit_one(self):
        left, right = self.workspace / "one.json", self.workspace / "two.json"
        with contextlib.redirect_stdout(io.StringIO()):
            main(["create", str(self.root), str(left)])
            (self.root / "new").touch()
            main(["create", str(self.root), str(right)])
        with contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(main(["diff", str(left), str(right), "--json"]), 1)
        self.assertEqual(json.loads(output.getvalue())["added"], ["new"])
