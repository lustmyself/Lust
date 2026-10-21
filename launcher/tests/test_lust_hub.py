import unittest
from unittest.mock import patch

from launcher import lust_hub


class TranslateTests(unittest.TestCase):
    def test_turkish_keeps_the_rest_of_the_message(self):
        with patch.object(lust_hub, "LANG", "tr"):
            self.assertEqual(lust_hub._translate("Extracting skins... 12 / 80"), "Skinler çıkarılıyor… 12 / 80")
            self.assertEqual(lust_hub._translate("Skins ready."), "Skinler hazır.")
            self.assertEqual(lust_hub._translate("Something new"), "Something new")

    def test_english_is_left_alone(self):
        with patch.object(lust_hub, "LANG", "en"):
            self.assertEqual(lust_hub._translate("Extracting skins..."), "Extracting skins...")


class HubDialogTests(unittest.TestCase):
    def setUp(self):
        self.dialog = lust_hub.HubDialog(show=False)

    def test_progress_is_clamped_and_marquee_clears_it(self):
        self.dialog.set_progress(140)
        self.assertEqual(lust_hub._state["progress"], 100)
        self.dialog.set_marquee(True)
        self.assertIsNone(lust_hub._state["progress"])

    def test_sizes_move_from_the_status_to_the_transfer_line(self):
        self.dialog.set_status("Extracting skins... 12.0 MB / 80.5 MB")
        self.assertEqual(lust_hub._state["status"], "Extracting skins...")
        self.assertEqual(lust_hub._state["transfer"], "12.0 MB / 80.5 MB")

    def test_byte_progress_sets_the_percentage(self):
        self.dialog.update_transfer_progress(50 * 1024 * 1024, 100 * 1024 * 1024)
        self.assertEqual(lust_hub._state["progress"], 50)
        self.assertEqual(lust_hub._state["transfer"], "50.0 MB / 100.0 MB")

    def test_pump_messages_keeps_the_launcher_loop_going(self):
        self.assertTrue(self.dialog.pump_messages(block=False))
        self.assertIsNone(self.dialog.hwnd)

    def test_update_prompt_falls_back_without_a_window(self):
        with patch.object(lust_hub, "take_update_acceptance", return_value=False), \
             patch("launcher.lust_autoupdate.enabled", return_value=False), \
             patch.object(lust_hub, "open_window", return_value=False), \
             patch.object(lust_hub, "WINDOW_WAIT_S", 0.2), \
             patch.object(lust_hub, "window_visible", return_value=False):
            self.assertIsNone(self.dialog.confirm_update("9.9.9", "1.0.0"))
        self.assertIsNone(lust_hub._state["prompt"])

    def test_auto_update_installs_without_asking(self):
        with patch.object(lust_hub, "take_update_acceptance", return_value=False), \
             patch("launcher.lust_autoupdate.enabled", return_value=True), \
             patch.object(lust_hub, "open_window") as open_window:
            self.assertTrue(self.dialog.confirm_update("9.9.9", "1.0.0"))
        open_window.assert_not_called()

    def test_update_accepted_in_the_hub_skips_the_prompt(self):
        with patch.object(lust_hub, "take_update_acceptance", return_value=True):
            self.assertTrue(self.dialog.confirm_update("9.9.9", "1.0.0"))


class ActionTests(unittest.TestCase):
    def test_action_message_becomes_a_toast(self):
        with patch.dict(lust_hub.ACTIONS, {"mods": lambda body: "done"}):
            self.assertEqual(lust_hub.run_action("mods"), "done")
        self.assertEqual(lust_hub._state["toast"]["text"], "done")

    def test_failing_action_is_reported_not_raised(self):
        def boom(body):
            raise RuntimeError("x")
        with patch.dict(lust_hub.ACTIONS, {"mods": boom}):
            self.assertTrue(lust_hub.run_action("mods"))

    def test_unknown_action_does_nothing(self):
        self.assertEqual(lust_hub.run_action("nope"), "")

    def test_status_action_takes_only_known_statuses(self):
        with patch.object(lust_hub, "_set_offline", return_value="") as set_offline:
            lust_hub.ACTIONS["status"]({"value": "../../x"})
            set_offline.assert_not_called()
            lust_hub.ACTIONS["status"]({"value": "offline"})
            set_offline.assert_called_once_with("offline")

    def test_prompt_answer_clears_the_prompt(self):
        lust_hub._set(prompt={"version": "9", "current": "1"})
        lust_hub.run_action("prompt", {"accept": True})
        self.assertIsNone(lust_hub._state["prompt"])
        self.assertTrue(lust_hub._prompt_answer)


class VersionTests(unittest.TestCase):
    def test_newer_release_is_offered(self):
        with patch.object(lust_hub, "APP_VERSION", "1.4.9.5"), \
             patch.object(lust_hub, "_cached", return_value=None):
            lust_hub._set(latest="1.4.9.6")
            self.assertTrue(lust_hub.snapshot()["update_available"])
            lust_hub._set(latest="1.4.9.5")
            self.assertFalse(lust_hub.snapshot()["update_available"])
            lust_hub._set(latest="1.4.10")
            self.assertTrue(lust_hub.snapshot()["update_available"])


class WindowTextTests(unittest.TestCase):
    def test_both_languages_have_every_text(self):
        from launcher.lust_hub_window import TEXT_STRINGS as TEXT
        self.assertEqual(set(TEXT["en"]), set(TEXT["tr"]))


if __name__ == "__main__":
    unittest.main()
