import subprocess
import sys
import threading
import time
import unittest
from unittest import mock

from launcher import lust_hub_shell


class _Window:
    def __init__(self):
        self.destroyed = threading.Event()

    def destroy(self):
        self.destroyed.set()


class CloseWithParentTests(unittest.TestCase):
    @unittest.skipUnless(sys.platform == "win32", "Windows process handles")
    def test_window_closes_when_lust_exits(self):
        parent = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(1)"])
        api = lust_hub_shell._Api()
        api._window = _Window()
        with mock.patch.object(lust_hub_shell.threading, "Timer") as timer:
            started = time.time()
            lust_hub_shell._close_with(parent.pid, api)
        self.assertTrue(api._window.destroyed.is_set())
        self.assertGreater(time.time() - started, 0.5)
        timer.assert_called_once()
        parent.wait()

    def test_parent_pid_is_read_from_the_command_line(self):
        with mock.patch.object(lust_hub_shell, "run") as run:
            self.assertTrue(lust_hub_shell.main_if_window(
                ["Lust.exe", lust_hub_shell.ARG, "http://127.0.0.1:47823/", lust_hub_shell.PARENT_ARG, "4242"]))
        run.assert_called_once_with("http://127.0.0.1:47823/", 4242)

    def test_old_command_line_without_parent(self):
        with mock.patch.object(lust_hub_shell, "run") as run:
            lust_hub_shell.main_if_window(["Lust.exe", lust_hub_shell.ARG, "http://127.0.0.1:47823/"])
        run.assert_called_once_with("http://127.0.0.1:47823/", 0)


class _Stop(Exception):
    pass


class HungWindowTests(unittest.TestCase):
    def _run_watch(self, hung_answers):
        from launcher import lust_hub
        sleeps = iter(range(len(hung_answers) + 2))

        def sleep(_seconds):
            if next(sleeps) >= len(hung_answers) + 1:
                raise _Stop

        with mock.patch.object(lust_hub.time, "sleep", side_effect=sleep), \
                mock.patch.object(lust_hub, "_window_hung", side_effect=hung_answers + [False] * 5), \
                mock.patch.object(lust_hub, "_kill_shell") as kill, \
                mock.patch.object(lust_hub, "open_window") as reopen, \
                mock.patch.object(lust_hub, "_reopens", 0), mock.patch.object(lust_hub, "_use_basic_window", False):
            with self.assertRaises(_Stop):
                lust_hub._watch_shell()
        return kill, reopen

    def test_a_locked_up_window_is_closed_and_opened_again(self):
        kill, reopen = self._run_watch([True, True, True])
        kill.assert_called_once()
        reopen.assert_called_once()

    def test_a_short_hiccup_is_left_alone(self):
        kill, reopen = self._run_watch([True, True, False, True])
        kill.assert_not_called()
        reopen.assert_not_called()

    def test_waits_for_the_previous_webview_on_the_same_folder(self):
        class Proc:
            def __init__(self, cmdline):
                self.info = {"name": "msedgewebview2.exe", "cmdline": cmdline}

        busy = [Proc(["msedgewebview2.exe", r"--user-data-dir=C:\Lust\hub-webview\EBWebView"])]
        answers = iter([busy, busy, []])
        with mock.patch("psutil.process_iter", side_effect=lambda *_: next(answers)), \
                mock.patch("time.sleep") as sleep:
            lust_hub_shell._wait_for_old_webview(r"C:\Lust\hub-webview")
        self.assertEqual(sleep.call_count, 2)


class ApiTests(unittest.TestCase):
    def test_the_page_sees_no_window_object(self):
        api = lust_hub_shell._Api()
        api._window = object()
        public = [name for name in vars(api) if not name.startswith("_")]
        self.assertEqual(public, [])


class UpdateScriptTests(unittest.TestCase):
    def test_update_closes_leftover_lust_windows_before_copying(self):
        from launcher.update.update_installer import APPLY_UPDATE_SCRIPT
        close = APPLY_UPDATE_SCRIPT.index("Closing Lust windows left open")
        self.assertLess(close, APPLY_UPDATE_SCRIPT.index("Mirroring files"))
        self.assertIn("Stop-Process", APPLY_UPDATE_SCRIPT)


class UpdateScriptOfflineTests(unittest.TestCase):
    def test_a_running_lust_offline_is_left_alone_and_a_failure_restarts_lust(self):
        from launcher.update.update_installer import APPLY_UPDATE_SCRIPT
        self.assertIn("%KEEP_OFFLINE%", APPLY_UPDATE_SCRIPT)
        self.assertLess(APPLY_UPDATE_SCRIPT.index('set "KEEP_OFFLINE='), APPLY_UPDATE_SCRIPT.index("robocopy"))
        failure = APPLY_UPDATE_SCRIPT[APPLY_UPDATE_SCRIPT.index(":robofail"):]
        self.assertNotIn("pause", failure)
        self.assertIn('start "" /D "%DEST%"', failure)

if __name__ == "__main__":
    unittest.main()
