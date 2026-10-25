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


class PriorityTests(unittest.TestCase):
    def test_only_lust_and_its_window_are_lowered_never_the_patcher(self):
        import psutil
        def proc(name):
            p = mock.Mock()
            p.name.return_value = name
            return p
        me = proc("Lust.exe")
        hub, webview, patcher = proc("Lust.exe"), proc("msedgewebview2.exe"), proc("ltk_patcher_host.exe")
        me.children.return_value = [hub, webview, patcher]
        with mock.patch.object(psutil, "Process", return_value=me), \
                mock.patch("sys.executable", "C:/Lust/Lust.exe"):
            procs = lust_perf._own_processes()
        self.assertEqual(procs, [me, hub, webview])

    def test_low_and_back_to_normal(self):
        import psutil
        me = mock.Mock()
        with mock.patch.object(lust_perf, "_own_processes", return_value=[me]), \
                mock.patch.object(psutil, "BELOW_NORMAL_PRIORITY_CLASS", 0x4000, create=True), \
                mock.patch.object(psutil, "NORMAL_PRIORITY_CLASS", 0x20, create=True):
            lust_perf.set_low_priority(True)
            lust_perf.set_low_priority(False)
        self.assertEqual([c.args[0] for c in me.nice.call_args_list], [0x4000, 0x20])


class MainLoopTests(unittest.TestCase):
    def test_the_main_loop_slows_down_during_a_match(self):
        from main.runtime.loop import _compute_main_loop_sleep
        state = mock.Mock(champion_exchange_triggered=False, chroma_panel_open=False,
                          pending_chroma_selection=False, phase="InProgress")
        self.assertEqual(_compute_main_loop_sleep(state, False), 0.5)
        state.phase = "ChampSelect"
        self.assertLess(_compute_main_loop_sleep(state, False), 0.5)
        state.phase = "InProgress"
        self.assertLess(_compute_main_loop_sleep(state, True), 0.5)
