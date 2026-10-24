import hashlib
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from injection.tools import ltk_manager, ltk_manager_setup as setup, patcher_manifest as pm
from injection.tools.patcher import LTK_PATCHER_DLL, LTK_PATCHER_HOST, LtkPatcherStatus

DAY = 24 * 60 * 60


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class ManifestTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.cache = self.root / pm.CACHE_FILE
        for target, value in ((pm, "_cache_path"),):
            p = patch.object(target, value, return_value=self.cache)
            p.start()
            self.addCleanup(p.stop)
        pm._memo.update(at=0.0, manifest=None)
        self.addCleanup(pm._memo.update, at=0.0, manifest=None)

    def _set(self, data):
        pm._memo.update(at=1.0, manifest=pm.clean(data))

    def test_without_network_or_copy_the_default_page_is_used(self):
        self.assertEqual(pm.download_url(), ltk_manager.PATCHER_URL)

    def test_the_kept_copy_is_used_without_the_network(self):
        self.cache.write_text(json.dumps({"downloads": [{"url": "https://example.com/new.zip"}]}), encoding="utf-8")
        self.assertEqual(pm.download_url(), "https://example.com/new.zip")

    def test_a_fetched_manifest_is_kept(self):
        response = MagicMock()
        response.json.return_value = {"downloads": [{"url": "https://example.com/a.zip"}]}
        with patch("requests.get", return_value=response):
            pm.manifest(refresh=True)
        self.assertEqual(pm.download_url(), "https://example.com/a.zip")
        self.assertIn("https://example.com/a.zip", self.cache.read_text(encoding="utf-8"))

    def test_a_failed_fetch_keeps_what_lust_had(self):
        self._set({"downloads": [{"url": "https://example.com/a.zip"}]})
        with patch("requests.get", side_effect=OSError("offline")):
            pm.manifest(refresh=True)
        self.assertEqual(pm.download_url(), "https://example.com/a.zip")

    def test_bad_entries_are_dropped(self):
        manifest = pm.clean({
            "downloads": [{"url": "http://plain.example.com/x.zip"}, {"url": 5}],
            "builds": [{"dll": "zz", "host": "a" * 64}, {"dll": "A" * 64, "host": "b" * 64, "eol": "soon"}],
            "locked": ["nothex", "c" * 64],
        })
        self.assertEqual(manifest["downloads"], pm.DEFAULT_MANIFEST["downloads"])
        self.assertEqual(manifest["builds"], [{"dll": "a" * 64, "host": "b" * 64, "eol": None, "note": ""}])
        self.assertEqual(manifest["locked"], ["c" * 64])
        self.assertIsNone(pm.clean([1, 2]))

    def test_known_build_needs_both_files(self):
        dll, host = self.root / "d.dll", self.root / "h.exe"
        dll.write_bytes(b"dll"), host.write_bytes(b"host")
        self._set({"builds": [{"dll": _sha(b"dll"), "host": _sha(b"host"), "eol": 500}]})
        self.assertEqual(pm.known_build(dll, host)["eol"], 500)
        self._set({"builds": [{"dll": _sha(b"dll"), "host": _sha(b"other")}]})
        self.assertIsNone(pm.known_build(dll, host))

    def test_a_listed_locked_build_counts_as_locked(self):
        (self.root / LTK_PATCHER_DLL).write_bytes(b"plain dll")
        self.assertFalse(ltk_manager.host_locked(self.root, self.root))
        self._set({"locked": [_sha(b"plain dll")]})
        self.assertTrue(ltk_manager.host_locked(self.root, self.root))


class UnsignedKnownBuildTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        self.downloads, self.tools, self.target = root / "Downloads", root / "tools", root / "ltk-patcher"
        self.downloads.mkdir()
        with zipfile.ZipFile(self.downloads / "ltk_patcher.zip", "w") as z:
            z.writestr(LTK_PATCHER_DLL, b"dll ok")
            z.writestr(LTK_PATCHER_HOST, b"host ok")
        p = patch.object(setup, "user_patcher_dir", return_value=self.target)
        p.start()
        self.addCleanup(p.stop)
        self.addCleanup(pm._memo.update, at=0.0, manifest=None)

    def _take(self):
        return setup.take_downloaded_patcher(self.tools, self.downloads, signature=lambda path: ("NotSigned", ""))

    def test_an_unsigned_build_the_manifest_lists_is_taken(self):
        pm._memo.update(at=1.0, manifest=pm.clean({"builds": [{"dll": _sha(b"dll ok"), "host": _sha(b"host ok")}]}))
        self.assertTrue(self._take())
        self.assertEqual((self.target / LTK_PATCHER_HOST).read_bytes(), b"host ok")

    def test_an_unsigned_unlisted_build_is_not_taken(self):
        pm._memo.update(at=1.0, manifest=pm.clean({}))
        self.assertFalse(self._take())


class ExpiringTests(unittest.TestCase):
    NOW = 1_800_000_000

    def _status(self, eol, expired=False, missing=()):
        s = MagicMock(spec=LtkPatcherStatus)
        s.missing, s.eol = list(missing), eol
        s.expired_for.return_value = expired
        return s

    def _soon(self, status):
        with patch.object(setup, "check_ltk_patcher", return_value=status):
            return setup.expiring_soon(Path("."), None, now=self.NOW)

    def test_an_end_of_life_within_days_is_told(self):
        self.assertEqual(self._soon(self._status(self.NOW + 2 * DAY)), self.NOW + 2 * DAY)

    def test_a_passed_end_of_life_before_league_updates_is_told(self):
        self.assertEqual(self._soon(self._status(self.NOW - DAY)), self.NOW - DAY)

    def test_far_off_expired_missing_or_unreadable_patchers_are_not(self):
        self.assertIsNone(self._soon(self._status(self.NOW + 30 * DAY)))
        self.assertIsNone(self._soon(self._status(self.NOW - DAY, expired=True)))
        self.assertIsNone(self._soon(self._status(None)))
        self.assertIsNone(self._soon(self._status(self.NOW, missing=[LTK_PATCHER_DLL])))


class HubStatusTests(unittest.TestCase):
    def tearDown(self):
        setup._tools_dir = None

    def test_before_the_startup_check_the_card_stays_hidden(self):
        setup._tools_dir = None
        self.assertEqual(setup.hub_status(), {"state": "ok"})

    def test_the_card_names_the_problem(self):
        setup._tools_dir = Path(".")
        with patch.object(setup, "_game_dir", return_value=None), \
                patch.object(setup, "patcher_problem", return_value="locked"), \
                patch.object(setup, "check_ltk_patcher", return_value=MagicMock(eol=None)):
            self.assertEqual(setup.hub_status()["state"], "locked")


if __name__ == "__main__":
    unittest.main()
