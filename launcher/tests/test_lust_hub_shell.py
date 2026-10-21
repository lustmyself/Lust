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
        api.window = _Window()
        with mock.patch.object(lust_hub_shell.threading, "Timer") as timer:
            started = time.time()
            lust_hub_shell._close_with(parent.pid, api)
        self.assertTrue(api.window.destroyed.is_set())
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


class UpdateScriptTests(unittest.TestCase):
    def test_update_closes_leftover_lust_windows_before_copying(self):
        from launcher.update.update_installer import APPLY_UPDATE_SCRIPT
        close = APPLY_UPDATE_SCRIPT.index("Closing Lust windows left open")
        self.assertLess(close, APPLY_UPDATE_SCRIPT.index("Mirroring files"))
        self.assertIn("Stop-Process", APPLY_UPDATE_SCRIPT)


if __name__ == "__main__":
    unittest.main()
