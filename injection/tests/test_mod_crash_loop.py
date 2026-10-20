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

# The patcher's events while a custom skin made for an older League crashed every game
# start (lust_runoverlay log, 2026-10-20): the client reconnected forever
CRASHING = """status 19.85 injecting game found
status 19.92 injected dll attached
status 19.92 waiting awaiting game exit
dll 21.85 63864 67016 INFO ltk_patcher_dll::hooks::fsov::imp: redirected wad: DATA/FINAL/Champions/Yone.wad.client
status 23.86 injecting scanning for game
status 24.73 exited dll detached
status 28.35 injecting game found
status 28.39 injected dll attached
status 28.39 waiting awaiting game exit
status 34.36 injecting scanning for game
status 34.69 exited dll detached
status 38.95 injecting game found
status 39.00 injected dll attached
"""


class ModCrashLoopTests(unittest.TestCase):
    def setUp(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        root = Path(temp_dir.name)
        self.events = root / "events.txt"
        self.overlay = OverlayManager(root / "tools", root / "mods", root / "game", ProcessManager())
        self.overlay._open_runoverlay_log = lambda: None
        reporter = patch.object(overlay_manager, "report_issue")
        reporter.start()
        self.addCleanup(reporter.stop)

    def _patcher(self, events: str):
        """A stand-in host that prints the events, then idles like the real one."""
        self.events.write_text(events, encoding="utf-8")
        script = (f"import sys,time; sys.stdout.write(open({str(self.events)!r}).read()); "
                  "sys.stdout.flush(); time.sleep(30)")
        real_popen = subprocess.Popen

        def popen(args, **kwargs):
            return real_popen([sys.executable, "-c", script], **kwargs)

        with patch.object(overlay_manager.subprocess, "Popen", popen), \
                patch("pengu.communication.lust_custom_skins.game_keeps_crashing") as crashed:
            session = self.overlay._start_ltk_patcher(Path(sys.executable), self.events.parent)
            self.addCleanup(lambda: session["proc"].poll() is None and session["proc"].kill())
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline and "39.00" not in str(session["session"].get("state")) \
                    and session["session"].get("state") != "injected":
                time.sleep(0.05)
            time.sleep(0.3)
        return session, crashed

    def test_a_game_closing_right_after_the_mods_load_stops_the_injection(self):
        session, crashed = self._patcher(CRASHING)
        self.assertTrue(session["session"].get("crash_loop"))
        crashed.assert_called_once()
        with patch.object(OverlayManager, "_running_game", return_value=None):
            code = self.overlay._run_ltk_patcher(session, self.events.parent)
        self.assertEqual(code, 1)
        self.assertIsNotNone(session["proc"].poll())  # the patcher was stopped

    def test_games_that_end_normally_are_not_a_crash_loop(self):
        with patch.object(overlay_manager, "QUICK_EXIT_S", 0.0):
            session, crashed = self._patcher(CRASHING)
        self.assertFalse(session["session"].get("crash_loop"))
        crashed.assert_not_called()

    def test_one_crash_is_not_enough(self):
        one = CRASHING.split("status 28.35")[0]
        session, crashed = self._patcher(one)
        self.assertFalse(session["session"].get("crash_loop"))
        crashed.assert_not_called()


if __name__ == "__main__":
    unittest.main()
