import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from launcher import lust_cleanup as cleanup
from launcher import lust_rose


class CleanUpdatesTests(unittest.TestCase):
    def test_old_packages_and_staging_go_newer_ones_stay(self):
        with tempfile.TemporaryDirectory() as tmp:
            updates = Path(tmp)
            for name in ("update_package_1.4.9.20.zip", "update_package_1.4.9.20.zip.ready",
                         "update_package_1.4.9.23.zip", "update_package_1.4.9.24.zip",
                         "update_package_1.4.9.24.zip.ready", "notes.txt"):
                (updates / name).write_text("x")
            (updates / "staging").mkdir()
            cleanup.clean_updates(updates, "1.4.9.23")
            self.assertEqual(sorted(p.name for p in updates.iterdir()),
                             ["notes.txt", "update_package_1.4.9.24.zip", "update_package_1.4.9.24.zip.ready"])


class CleanOldInstallsTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.here = self.root / "Lust"
        self.here.mkdir()

    def _run(self, entries):
        deleted = []
        with patch.object(cleanup, "_entries", return_value=iter(entries)), \
                patch.object(cleanup, "_delete_entry", side_effect=lambda view, app_id: deleted.append(app_id)):
            cleanup.clean_old_installs(self.here)
        return deleted

    def test_duplicate_entry_for_this_install_is_removed_files_stay(self):
        (self.here / "Lust.exe").write_text("x")
        deleted = self._run([(0, "old", {"DisplayName": "Lust", "InstallLocation": f'"{self.here}"'})])
        self.assertEqual(deleted, ["old"])
        self.assertTrue((self.here / "Lust.exe").exists())

    def test_a_lust_copy_elsewhere_goes_with_its_entry(self):
        old = self.root / "Old"
        old.mkdir()
        (old / "Lust.exe").write_text("x")
        deleted = self._run([(0, "old", {"DisplayName": "Lust", "InstallLocation": str(old)})])
        self.assertEqual(deleted, ["old"])
        self.assertFalse(old.exists())

    def test_roses_entry_and_folders_with_rose_are_left_alone(self):
        rose = self.root / "Rose"
        rose.mkdir()
        (rose / "Rose.exe").write_text("x")
        (rose / "Lust.exe").write_text("x")
        deleted = self._run([
            (0, "rose", {"DisplayName": "Rose", "InstallLocation": str(rose)}),
            (0, "mixed", {"DisplayName": "Lust", "InstallLocation": str(rose)}),
        ])
        self.assertEqual(deleted, [])
        self.assertTrue((rose / "Rose.exe").exists())


class RoseGuardTests(unittest.TestCase):
    def test_takes_back_only_a_hook_that_runs_roses_loader(self):
        with patch("utils.integration.pengu_loader._hook_of_another_loader",
                   return_value=Path(r"C:\Program Files\Rose\_internal\Pengu Loader\core.dll")), \
                patch("utils.integration.pengu_loader.activate", return_value=True) as activate:
            self.assertTrue(lust_rose._take_back_hook())
            activate.assert_called_once()
        with patch("utils.integration.pengu_loader._hook_of_another_loader",
                   return_value=Path(r"C:\Tools\Pengu Loader\core.dll")), \
                patch("utils.integration.pengu_loader.activate") as activate:
            self.assertFalse(lust_rose._take_back_hook())
            activate.assert_not_called()


if __name__ == "__main__":
    unittest.main()
