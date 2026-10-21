import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from injection.tools import ltk_manager_setup as setup
from injection.tools.patcher import LTK_PATCHER_DLL, LTK_PATCHER_HOST, LtkPatcherStatus


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
        p = patch.object(setup, "import_from_ltk_manager", side_effect=self._import)
        p.start()
        self.addCleanup(p.stop)
        self.imports_succeed = False
        self.statuses = []  # returned by check_ltk_patcher, in order
        p = patch.object(setup, "check_ltk_patcher", side_effect=lambda d: self.statuses.pop(0))
        p.start()
        self.addCleanup(p.stop)

    def _import(self, tools_dir):
        self.calls.append("import")
        return self.tools if self.imports_succeed and "installer" in self.calls else None

    def _run(self, answer=True, fetch_error=None, installed=None):
        def ask(kind):
            self.calls.append(f"ask:{kind}")
            return answer

        def fetch(work):
            self.calls.append("fetch")
            if fetch_error:
                raise fetch_error
            return work / "LTK.Manager_1.28.1_x64-setup.exe"

        def run_installer(path):
            self.calls.append("installer")

        def run_silent(path):
            self.calls.append("silent")

        errors = []
        setup.ensure_ltk_patcher(self.tools, None, ask=ask, fetch=fetch,
                                 run_installer=run_installer, report_error=errors.append,
                                 installed=lambda: installed, run_silent=run_silent,
                                 background=lambda tools: self.calls.append("background"))
        return errors

    def test_installed_ltk_manager_is_checked_in_the_background(self):
        self.statuses = [_status()]
        self._run(installed="1.28.1")
        self.assertEqual(self.calls, ["import", "background"])

    def test_expired_patcher_of_an_installed_manager_updates_silently(self):
        self.statuses = [_status(expired=True), _status()]
        self.imports_succeed = True
        self.calls_before = []

        def import_after_silent(tools_dir):
            self.calls.append("import")
            return self.tools if "silent" in self.calls else None
        with patch.object(setup, "import_from_ltk_manager", side_effect=import_after_silent):
            self._run(installed="1.27.0")
        self.assertEqual(self.calls, ["import", "fetch", "silent", "import"])
        self.assertNotIn("installer", self.calls)
        self.assertFalse(any(call.startswith("ask") for call in self.calls))

    def test_versions_compare_by_number(self):
        self.assertGreater(setup._version("v1.28.10"), setup._version("1.28.9"))
        self.assertEqual(setup._version("v1.28.1"), setup._version("1.28.1"))

    def test_latest_release_falls_back_to_github_com(self):
        session = MagicMock()
        session.get.side_effect = [setup.requests.HTTPError("403 rate limit"),
                                   MagicMock(status_code=302, headers={
                                       "Location": "https://github.com/LeagueToolkit/ltk-manager/releases/tag/v1.29.0"})]
        session.head.return_value = MagicMock(headers={"Content-Length": "123"})
        tag, url, size = setup.latest_release(session)
        self.assertEqual((tag, size), ("v1.29.0", 123))
        self.assertEqual(url, setup.DOWNLOAD_PREFIX + "v1.29.0/LTK.Manager_1.29.0_x64-setup.exe")

    def test_usable_patcher_asks_nothing(self):
        self.statuses = [_status()]
        self._run()
        self.assertEqual(self.calls, ["import"])

    def test_missing_patcher_asks_downloads_and_opens_installer(self):
        self.statuses = [_status(missing=[LTK_PATCHER_DLL]), _status(missing=[LTK_PATCHER_DLL])]
        self.imports_succeed = True
        self.assertEqual(self._run(), [])
        self.assertEqual(self.calls, ["import", "ask:install", "fetch", "installer", "import"])

    def test_expired_patcher_offers_an_update(self):
        self.statuses = [_status(expired=True), _status(expired=True)]
        self.imports_succeed = True
        self._run()
        self.assertIn("ask:update", self.calls)

    def test_declining_downloads_nothing(self):
        self.statuses = [_status(missing=[LTK_PATCHER_HOST]), _status(missing=[LTK_PATCHER_HOST])]
        self._run(answer=False)
        self.assertEqual(self.calls, ["import", "ask:install"])

    def test_failed_download_is_reported_and_nothing_runs(self):
        self.statuses = [_status(eol=None), _status(eol=None)]
        errors = self._run(fetch_error=setup.SetupError("not signed"))
        self.assertEqual(errors, ["not signed"])
        self.assertNotIn("installer", self.calls)


class ReleaseAndSignatureTests(unittest.TestCase):
    def _session(self, assets):
        session = MagicMock()
        session.get.return_value.json.return_value = {"tag_name": "v1.28.1", "assets": assets}
        return session

    def test_picks_the_official_windows_installer(self):
        url = setup.DOWNLOAD_PREFIX + "v1.28.1/LTK.Manager_1.28.1_x64-setup.exe"
        session = self._session([
            {"name": "latest.json", "browser_download_url": setup.DOWNLOAD_PREFIX + "v1.28.1/latest.json", "size": 1},
            {"name": "LTK.Manager_1.28.1_x64-setup.exe.sig", "browser_download_url": url + ".sig", "size": 1},
            {"name": "LTK.Manager_1.28.1_x64-setup.exe", "browser_download_url": url, "size": 21808624},
        ])
        self.assertEqual(setup.latest_release(session), ("v1.28.1", url, 21808624))

    def test_refuses_installers_hosted_elsewhere(self):
        session = self._session([{"name": "LTK.Manager_1.28.1_x64-setup.exe",
                                  "browser_download_url": "https://evil.example/LTK.Manager_1.28.1_x64-setup.exe",
                                  "size": 10}])
        with self.assertRaises(setup.SetupError):
            setup.latest_release(session)

    def test_signature_must_be_valid_and_from_league_toolkit(self):
        official = "CN=Natoken LLC, O=Natoken LLC, L=Austin, S=Texas, C=US"
        for status, subject, ok in (
            ("Valid", official, True),
            ("NotSigned", "", False),
            ("HashMismatch", official, False),
            ("Valid", "CN=Someone Else, O=Someone Else", False),
        ):
            with self.subTest(status=status, subject=subject), \
                    patch.object(setup, "signature_of", return_value=(status, subject)):
                if ok:
                    setup.verify_signature(Path("x.exe"))
                else:
                    with self.assertRaises(setup.SetupError):
                        setup.verify_signature(Path("x.exe"))


if __name__ == "__main__":
    unittest.main()
