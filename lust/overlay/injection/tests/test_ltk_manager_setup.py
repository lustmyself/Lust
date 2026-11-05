import tempfile
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


class StartupCheckTests(unittest.TestCase):
    def _run(self, problem):
        calls = []
        with patch.object(setup, "manifest"), patch.object(setup, "_game_dir", return_value=None), \
                patch.object(setup, "take_downloaded_patcher", side_effect=lambda *a: calls.append("take")), \
                patch.object(setup, "import_from_ltk_manager", side_effect=lambda *a: calls.append("import")), \
                patch.object(setup, "patcher_problem", return_value=problem), \
                patch.object(setup, "warn_if_host_locked", return_value=False), \
                patch.object(setup, "warn_if_expiring", return_value=False), \
                patch("webbrowser.open", side_effect=AssertionError("opened a download page")):
            setup.startup_check(self.tools)
        return calls

    def setUp(self):
        self.tools = Path(tempfile.mkdtemp())

    def test_takes_a_downloaded_patcher_without_asking(self):
        for problem in (None, "missing", "locked", "expired"):
            with self.subTest(problem=problem):
                self.assertEqual(self._run(problem), ["take", "import"])

    def test_no_dialog_left_to_show(self):
        for name in ("ensure_ltk_patcher", "ask_to_download", "wait_for_download", "hub_download"):
            self.assertFalse(hasattr(setup, name), name)

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
