import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from injection.tools import ltk_manager
from injection.tools.patcher import LTK_PATCHER_DLL, LTK_PATCHER_HOST, LtkPatcherStatus


def _write_patcher(folder: Path, tag: str) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    (folder / LTK_PATCHER_HOST).write_text(f"host {tag}")
    (folder / LTK_PATCHER_DLL).write_text(f"dll {tag}")


class ImportFromLtkManagerTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.tools = self.root / "tools"
        self.eols = {}  # folder -> EOL the fake check reports
        for target in ("_registry_install_dirs", "_default_install_dirs"):
            p = patch.object(ltk_manager, target, return_value=[])
            p.start()
            self.addCleanup(p.stop)
        p = patch.object(ltk_manager, "check_ltk_patcher", side_effect=self._fake_check)
        p.start()
        self.addCleanup(p.stop)

    def tearDown(self):
        self._tmp.cleanup()

    def _fake_check(self, folder):
        host, dll = folder / LTK_PATCHER_HOST, folder / LTK_PATCHER_DLL
        missing = [f.name for f in (host, dll) if not f.is_file()]
        eol = None if missing else self.eols.get(folder)
        return LtkPatcherStatus(host=host, dll=dll, missing=missing, eol=eol)

    def _ltk(self, name, eol):
        folder = self.root / name
        _write_patcher(folder, name)
        self.eols[folder] = eol
        return folder

    def test_copies_both_files_when_lust_has_none(self):
        ltk = self._ltk("ltk", 100)
        self.assertEqual(ltk_manager.import_from_ltk_manager(self.tools, [ltk]), ltk)
        self.assertEqual((self.tools / LTK_PATCHER_HOST).read_text(), "host ltk")
        self.assertEqual((self.tools / LTK_PATCHER_DLL).read_text(), "dll ltk")
        self.assertEqual(sorted(p.name for p in self.tools.iterdir()), [LTK_PATCHER_DLL, LTK_PATCHER_HOST])

    def test_keeps_lust_copy_when_it_is_as_new(self):
        _write_patcher(self.tools, "mine")
        self.eols[self.tools] = 200
        ltk = self._ltk("ltk", 150)
        self.assertIsNone(ltk_manager.import_from_ltk_manager(self.tools, [ltk]))
        self.assertEqual((self.tools / LTK_PATCHER_DLL).read_text(), "dll mine")

    def test_replaces_older_or_unreadable_copy_with_newest_install(self):
        _write_patcher(self.tools, "mine")
        self.eols[self.tools] = None  # unrecognized DLL
        old, new = self._ltk("old", 100), self._ltk("new", 300)
        self.assertEqual(ltk_manager.import_from_ltk_manager(self.tools, [old, new]), new)
        self.assertEqual((self.tools / LTK_PATCHER_DLL).read_text(), "dll new")

    def test_ignores_installs_with_an_unrecognized_dll(self):
        bad = self._ltk("bad", None)
        self.assertIsNone(ltk_manager.import_from_ltk_manager(self.tools, [bad]))
        self.assertFalse((self.tools / LTK_PATCHER_DLL).exists())

    def test_nothing_to_do_without_ltk_manager(self):
        self.assertIsNone(ltk_manager.import_from_ltk_manager(self.tools, []))

    def test_only_folders_with_both_files_count(self):
        half = self.root / "half"
        half.mkdir()
        (half / LTK_PATCHER_DLL).write_text("dll")
        self.assertEqual(ltk_manager.find_ltk_manager_patchers([half]), [])


if __name__ == "__main__":
    unittest.main()
