import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from injection.overlay import overlay_manager
from injection.overlay.overlay_manager import OverlayManager
from injection.overlay.process_manager import ProcessManager
from injection.tools import ltk_manager
from injection.tools.patcher import LTK_PATCHER_DLL, LTK_PATCHER_HOST, LtkPatcherStatus

# The patcher's events when a build from LTK Manager 1.30 refused Lust (lust_runoverlay log, 2026-10-23)
REFUSED = """status 33.6029264 injecting game found
status 33.7343830 injected dll attached
status 33.7343830 waiting awaiting game exit
dll 33.7343830 6608 16984 INFO ltk_patcher_dll::entry: init in process
dll 33.7368983 6608 16984 INFO ltk_patcher_dll::entry: init done
dll 35.8940836 6608 22180 ERROR ltk_patcher_dll::verify: host verification failed, refusing overlay: [VRF00000008] (18320,ltk-manager.exe)
"""
LOCKED_DLL = "dll with ltk_patcher_dll::verify: host verification failed, refusing overlay"


class RefusedHostTests(unittest.TestCase):
    def setUp(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        root = Path(temp_dir.name)
        self.events = root / "events.txt"
        self.overlay = OverlayManager(root / "tools", root / "mods", root / "game", ProcessManager())
        self.overlay._open_runoverlay_log = lambda: None
        reporter = patch.object(overlay_manager, "report_issue")
        self.report = reporter.start()
        self.addCleanup(reporter.stop)

    def test_a_refused_host_is_told_to_the_player_once(self):
        self.events.write_text(REFUSED, encoding="utf-8")
        script = (f"import sys,time; sys.stdout.write(open({str(self.events)!r}).read()); "
                  "sys.stdout.flush(); time.sleep(30)")
        real_popen = subprocess.Popen

        def popen(args, **kwargs):
            return real_popen([sys.executable, "-c", script], **kwargs)

        with patch.object(overlay_manager.subprocess, "Popen", popen), \
                patch.object(ltk_manager, "patcher_refused_host") as refused:
            session = self.overlay._start_ltk_patcher(Path(sys.executable), self.events.parent)
            self.addCleanup(lambda: session["proc"].poll() is None and session["proc"].kill())
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline and not session["session"].get("host_locked"):
                time.sleep(0.05)
        self.assertTrue(session["session"].get("host_locked"))
        refused.assert_called_once()
        self.assertEqual(refused.call_args.args[0], Path(sys.executable).parent)
        with patch.object(OverlayManager, "_running_game", return_value=None):
            code = self.overlay._run_ltk_patcher(session, self.events.parent, stop_callback=lambda: True)
        self.assertEqual(code, 1)
        self.report.assert_not_called()  # no generic "LTK patcher failed" on top


class LockedCauseTests(unittest.TestCase):
    def test_troubleshooting_names_the_lock(self):
        self.assertEqual(overlay_manager.ltk_failure_cause(
            "Skins will not load: this LTK patcher only runs inside LTK Manager (host verification)."), "locked")
        self.assertEqual(overlay_manager.ltk_failure_cause(REFUSED.splitlines()[-1]), "locked")


class HostLockedImportTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.tools = self.root / "tools"
        self.backup = self.tools / ltk_manager.BACKUP_DIR
        self.eols = {}
        for target in ("_registry_install_dirs", "_default_install_dirs"):
            p = patch.object(ltk_manager, target, return_value=[])
            p.start()
            self.addCleanup(p.stop)
        p = patch.object(ltk_manager, "check_ltk_patcher", side_effect=self._fake_check)
        p.start()
        self.addCleanup(p.stop)
        p = patch.object(ltk_manager, "_tell_player")
        self.told = p.start()
        self.addCleanup(p.stop)

    def _fake_check(self, folder):
        host, dll = folder / LTK_PATCHER_HOST, folder / LTK_PATCHER_DLL
        missing = [f.name for f in (host, dll) if not f.is_file()]
        return LtkPatcherStatus(host=host, dll=dll, missing=missing, eol=None if missing else self.eols.get(folder))

    def _patcher(self, folder, dll_text, eol):
        folder.mkdir(parents=True, exist_ok=True)
        (folder / LTK_PATCHER_HOST).write_text(f"host {dll_text}")
        (folder / LTK_PATCHER_DLL).write_text(dll_text)
        self.eols[folder] = eol
        return folder

    def _dll(self, folder):
        return (folder / LTK_PATCHER_DLL).read_text()

    def test_a_locked_build_is_never_copied_over_a_working_one(self):
        self._patcher(self.tools, "dll mine", 100)
        ltk = self._patcher(self.root / "ltk", LOCKED_DLL, 300)
        self.assertIsNone(ltk_manager.import_from_ltk_manager(self.tools, [ltk]))
        self.assertEqual(self._dll(self.tools), "dll mine")

    def test_the_working_copy_is_kept_when_a_newer_one_replaces_it(self):
        self._patcher(self.tools, "dll mine", 100)
        ltk = self._patcher(self.root / "ltk", "dll new", 300)
        self.assertEqual(ltk_manager.import_from_ltk_manager(self.tools, [ltk]), ltk)
        self.assertEqual(self._dll(self.tools), "dll new")
        self.assertEqual(self._dll(self.backup), "dll mine")

    def test_a_locked_copy_is_replaced_by_an_older_unlocked_one(self):
        self._patcher(self.tools, LOCKED_DLL, 300)
        own = self._patcher(self.root / "own", "dll own", 100)
        self.assertEqual(ltk_manager.import_from_ltk_manager(self.tools, [own]), own)
        self.assertEqual(self._dll(self.tools), "dll own")
        self.assertFalse(self.backup.exists())  # a locked copy is not worth keeping

    def test_a_locked_copy_comes_back_from_the_backup(self):
        self._patcher(self.tools, LOCKED_DLL, 300)
        self._patcher(self.backup, "dll mine", 100)
        self.assertEqual(ltk_manager.import_from_ltk_manager(self.tools, []), self.backup)
        self.assertEqual(self._dll(self.tools), "dll mine")

    def test_a_build_that_refused_lust_is_never_taken_again(self):
        self._patcher(self.tools, "dll refusing", 300)
        ltk_manager.patcher_refused_host(self.tools, "host verification failed, refusing overlay: [VRF00000008]")
        self.told.assert_called_once()
        self.assertTrue(ltk_manager.host_locked(self.tools, self.tools))
        ltk = self._patcher(self.root / "ltk", "dll refusing", 300)
        self._patcher(self.backup, "dll mine", 100)
        self.assertEqual(ltk_manager.import_from_ltk_manager(self.tools, [ltk]), self.backup)
        self.assertEqual(self._dll(self.tools), "dll mine")

    def test_startup_warns_only_about_a_locked_copy(self):
        self._patcher(self.tools, "dll mine", 100)
        self.assertFalse(ltk_manager.warn_if_host_locked(self.tools))
        self.told.assert_not_called()
        self._patcher(self.tools, LOCKED_DLL, 300)
        self.assertTrue(ltk_manager.warn_if_host_locked(self.tools))
        self.told.assert_called_once()


class DownloadedZipTests(unittest.TestCase):
    def setUp(self):
        from injection.tools import ltk_manager_setup as setup
        self.setup = setup
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        self.downloads, self.tools, self.target = root / "Downloads", root / "tools", root / "ltk-patcher"
        self.downloads.mkdir()
        p = patch.object(setup, "user_patcher_dir", return_value=self.target)
        p.start()
        self.addCleanup(p.stop)

    def _zip(self, dll=b"dll ok", host=b"host ok", name="ltk_patcher.zip", folder="ltk_patcher/"):
        import zipfile
        with zipfile.ZipFile(self.downloads / name, "w") as z:
            if dll is not None:
                z.writestr(folder + LTK_PATCHER_DLL, dll)
            z.writestr(folder + LTK_PATCHER_HOST, host)

    def _take(self, signer="CN=Natoken LLC, O=Natoken LLC", status="Valid"):
        return self.setup.take_downloaded_patcher(self.tools, self.downloads, signature=lambda path: (status, signer))

    def test_a_signed_unlocked_zip_is_taken_once(self):
        self._zip()
        self.assertTrue(self._take())
        self.assertEqual((self.target / LTK_PATCHER_DLL).read_bytes(), b"dll ok")
        self.assertEqual((self.target / LTK_PATCHER_HOST).read_bytes(), b"host ok")
        self.assertFalse(self._take())  # the same files at the next start

    def test_a_locked_zip_is_not_taken(self):
        self._zip(dll=LOCKED_DLL.encode())
        self.assertFalse(self._take())
        self.assertFalse(self.target.exists())

    def test_an_unsigned_zip_is_not_taken(self):
        self._zip()
        self.assertFalse(self._take(status="NotSigned", signer=""))
        self.assertFalse(self._take(signer="CN=Someone Else"))
        self.assertFalse(self.target.exists())

    def test_a_zip_without_both_files_is_not_taken(self):
        self._zip(dll=None)
        self.assertFalse(self._take())

    def test_other_zips_are_ignored(self):
        self._zip(name="skins.zip")
        self.assertFalse(self._take())


if __name__ == "__main__":
    unittest.main()
