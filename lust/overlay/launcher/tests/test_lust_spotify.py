import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from launcher import lust_spotify as spotify


class ReapplyTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.exe = self.root / "Spotify.exe"
        self.exe.write_bytes(b"v1")
        for target, value in (("get_user_data_dir", self.root), ("spotify_exe", self.exe)):
            patcher = patch.object(spotify, target, return_value=value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_applies_again_only_after_spotify_changed(self):
        spotify._save({"theme": "lust", "auto": True, "marker": spotify._marker(self.exe)})
        with patch.object(spotify, "_run") as run:
            self.assertIsNone(spotify.reapply_if_updated())
            run.assert_not_called()
            self.exe.write_bytes(b"version two")
            self.assertTrue(spotify.reapply_if_updated())
            run.assert_called_once_with("backup", "apply")
            self.assertIsNone(spotify.reapply_if_updated())  # marker updated

    def test_nothing_without_a_theme_or_with_auto_off(self):
        self.exe.write_bytes(b"changed")
        with patch.object(spotify, "_run") as run:
            spotify._save({"theme": "", "auto": True, "marker": "old"})
            self.assertIsNone(spotify.reapply_if_updated())
            spotify._save({"theme": "lust", "auto": False})
            self.assertIsNone(spotify.reapply_if_updated())
            run.assert_not_called()

    def test_unknown_theme_is_ignored(self):
        self.assertEqual(spotify.apply("../evil"), "")


if __name__ == "__main__":
    unittest.main()
