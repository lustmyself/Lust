import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from injection.tools import ltk_manager_setup as setup
from injection.tools.patcher import LTK_PATCHER_DLL, LtkPatcherStatus


def _status(missing=(), eol=100, expired=False):
    s = MagicMock(spec=LtkPatcherStatus)
    s.missing = list(missing)
    s.eol = eol
    s.expired_for.return_value = expired
    return s


class EnsurePatcherTests(unittest.TestCase):
    def setUp(self):
        self.tools = Path(tempfile.mkdtemp())
        self.calls = []
        self.problems = []  # returned by patcher_problem, in order
        for name in ("take_downloaded_patcher", "import_from_ltk_manager"):
            p = patch.object(setup, name, side_effect=lambda *a, n=name: self.calls.append(n.split("_")[0]))
            p.start()
            self.addCleanup(p.stop)
        p = patch.object(setup, "patcher_problem", side_effect=lambda *a: self.problems.pop(0))
        p.start()
        self.addCleanup(p.stop)

    def _run(self, answer=True, arrives=True):
        def ask(problem):
            self.calls.append(f"ask:{problem}")
            return answer

        def wait(ready):
            self.calls.append("wait")
            return ready() if arrives else False

        return setup.ensure_ltk_patcher(self.tools, None, ask=ask, wait=wait,
                                        open_page=lambda url: self.calls.append(f"open:{url}"))

    def test_usable_patcher_asks_nothing(self):
        self.problems = [None]
        self.assertTrue(self._run())
        self.assertEqual(self.calls, ["take", "import"])

    def test_missing_patcher_opens_the_zip_page_and_waits_for_it(self):
        self.problems = ["missing", None]
        self.assertTrue(self._run())
        self.assertEqual(self.calls, ["take", "import", "ask:missing", f"open:{setup.PATCHER_URL}", "wait",
                                      "take", "import"])

    def test_locked_and_expired_patchers_ask_too(self):
        for problem in ("locked", "expired"):
            with self.subTest(problem=problem):
                self.calls, self.problems = [], [problem]
                self.assertFalse(self._run(answer=False))
                self.assertEqual(self.calls, ["take", "import", f"ask:{problem}"])

    def test_nothing_arriving_leaves_it_unusable(self):
        self.problems = ["missing"]
        self.assertFalse(self._run(arrives=False))

    def test_ltk_manager_is_never_installed(self):
        for name in ("download_verified_installer", "open_installer", "run_installer_silently",
                     "update_installed", "ask_to_install"):
            self.assertFalse(hasattr(setup, name), name)


class PatcherProblemTests(unittest.TestCase):
    def _problem(self, status, locked=False, expired=False):
        status.expired_for.return_value = expired
        with patch.object(setup, "check_ltk_patcher", return_value=status), \
                patch.object(setup, "host_locked", return_value=locked):
            return setup.patcher_problem(Path("tools"), None)

    def test_each_problem(self):
        self.assertEqual(self._problem(_status(missing=[LTK_PATCHER_DLL])), "missing")
        self.assertEqual(self._problem(_status(eol=None)), "missing")
        self.assertEqual(self._problem(_status(), locked=True), "locked")
        self.assertEqual(self._problem(_status(), expired=True), "expired")
        self.assertIsNone(self._problem(_status()))


class WaitTests(unittest.TestCase):
    def _wait(self, ready, dialog_s=0.5, timeout_s=5):
        # Stands in for the marquee window: open for dialog_s, as if the player left it alone
        with patch.object(setup, "_run_task_dialog", side_effect=lambda *a, **k: time.sleep(dialog_s)):
            return setup.wait_for_download(ready, timeout_s=timeout_s, poll_s=0.05)

    def test_returns_once_the_patcher_is_ready(self):
        checks = iter([False, False, True])
        self.assertTrue(self._wait(lambda: next(checks)))

    def test_a_closed_window_stops_the_wait(self):
        self.assertFalse(self._wait(lambda: False, dialog_s=0.2))

    def test_a_failing_check_is_tried_again(self):
        checks = iter([OSError("half written"), True])

        def ready():
            value = next(checks)
            if isinstance(value, Exception):
                raise value
            return value
        self.assertTrue(self._wait(ready))


class SignatureTests(unittest.TestCase):
    def test_signature_must_be_valid_and_from_league_toolkit(self):
        official = "CN=Natoken LLC, O=Natoken LLC, L=Austin, S=Texas, C=US"
        for status, subject, ok in (
            ("Valid", official, True),
            ("NotSigned", "", False),
            ("HashMismatch", official, False),
            ("Valid", "CN=Someone Else, O=Someone Else", False),
        ):
            with self.subTest(status=status, subject=subject):
                self.assertEqual(setup._signed_by_ltk((status, subject)), ok)


if __name__ == "__main__":
    unittest.main()
