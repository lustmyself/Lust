import io
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from launcher import lust_autoupdate as auto


def _zip_bytes() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("Lust.exe", b"x" * 100)
    return buffer.getvalue()


def _response(data: bytes):
    response = MagicMock()
    response.__enter__.return_value = response
    response.iter_content.return_value = [data]
    return response


class AutoUpdateTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)
        patcher = patch.object(auto, "_updates_dir", return_value=self.dir)
        patcher.start()
        self.addCleanup(patcher.stop)
        auto._pending = None

    def test_a_complete_download_is_ready(self):
        target = self.dir / "update_package_9.zip"
        data = _zip_bytes()
        with patch.object(auto.requests, "get", return_value=_response(data)):
            self.assertTrue(auto._download("https://x", target, len(data)))
        self.assertTrue(auto.is_ready(target))
        target.write_bytes(data + b"more")  # changed afterwards: not the package that was checked
        self.assertFalse(auto.is_ready(target))

    def test_a_damaged_or_short_download_is_dropped(self):
        target = self.dir / "update_package_9.zip"
        with patch.object(auto.requests, "get", return_value=_response(b"not a zip")):
            self.assertFalse(auto._download("https://x", target))
        data = _zip_bytes()
        with patch.object(auto.requests, "get", return_value=_response(data)):
            self.assertFalse(auto._download("https://x", target, len(data) + 5))
        self.assertFalse(target.exists())
        self.assertEqual(list(self.dir.iterdir()), [])

    def _client(self, version):
        client = MagicMock()
        client.get_release_version.return_value = f"v{version}"
        client.get_zip_asset.return_value = {"name": f"update_package_{version}.zip",
                                             "browser_download_url": "https://x", "size": 0}
        return client

    def test_only_newer_releases_download_and_only_when_on(self):
        with patch.object(auto, "_download", return_value=True) as download, \
                patch.object(auto, "enabled", return_value=True), \
                patch.object(auto.threading, "Thread"), patch("launcher.lust_hub.toast"):
            auto.on_release(self._client("1.4.9.1"), {}, "1.4.9.5")
            download.assert_not_called()
            auto.on_release(self._client("1.4.9.9"), {}, "1.4.9.5")
            download.assert_called_once()
            self.assertEqual(auto.pending(), "1.4.9.9")
        auto._pending = None
        with patch.object(auto, "_download") as download, patch.object(auto, "enabled", return_value=False):
            auto.on_release(self._client("1.4.9.9"), {}, "1.4.9.5")
            download.assert_not_called()

    def test_installs_only_after_league_was_closed_twice(self):
        auto._pending = "1.4.9.9"
        states = iter([True, False, True, False, False])
        with patch.object(auto, "_league_running", side_effect=lambda: next(states)), \
                patch.object(auto, "enabled", return_value=True), patch.object(auto, "IDLE_CHECK_S", 0), \
                patch.object(auto.time, "sleep"), patch("launcher.lust_hub.toast"), \
                patch("launcher.lust_hub.run_action") as run:
            auto._install_when_idle("1.4.9.9")
        run.assert_called_once_with("update")


if __name__ == "__main__":
    unittest.main()
