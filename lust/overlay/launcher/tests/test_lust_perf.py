import unittest
from unittest import mock

from launcher import lust_perf


class PerformanceModeTests(unittest.TestCase):
    def setUp(self):
        lust_perf._checked_at = 0.0

    def test_rests_only_during_a_match_with_the_switch_on(self):
        with mock.patch.object(lust_perf, "_game_running", return_value=True), \
                mock.patch("launcher.lust_settings.enabled", return_value=True):
            self.assertTrue(lust_perf.resting())
        lust_perf._checked_at = 0.0
        with mock.patch.object(lust_perf, "_game_running", return_value=False), \
                mock.patch("launcher.lust_settings.enabled", return_value=True):
            self.assertFalse(lust_perf.resting())

    def test_switched_off_never_rests(self):
        with mock.patch.object(lust_perf, "_game_running", return_value=True), \
                mock.patch("launcher.lust_settings.enabled", return_value=False):
            self.assertFalse(lust_perf.resting())

    def test_the_process_list_is_read_at_most_every_few_seconds(self):
        with mock.patch.object(lust_perf, "_game_running", return_value=True) as scan:
            for _ in range(5):
                lust_perf.in_game()
        scan.assert_called_once()

    def test_a_failing_scan_does_not_rest(self):
        with mock.patch.object(lust_perf, "_game_running", side_effect=OSError("denied")):
            self.assertFalse(lust_perf.in_game())

    def test_no_update_download_during_a_match(self):
        from launcher import lust_autoupdate
        client = mock.Mock()
        client.get_release_version.return_value = "v99.0"
        with mock.patch.object(lust_autoupdate, "enabled", return_value=True), \
                mock.patch.object(lust_perf, "resting", return_value=True), \
                mock.patch.object(lust_autoupdate, "_download") as download:
            lust_autoupdate.on_release(client, {}, "1.0")
        download.assert_not_called()
        client.get_zip_asset.assert_not_called()


if __name__ == "__main__":
    unittest.main()
