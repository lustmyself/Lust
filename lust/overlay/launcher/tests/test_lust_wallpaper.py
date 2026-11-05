import unittest
from unittest import mock

from launcher import lust_wallpaper


class CleanTests(unittest.TestCase):
    def test_bad_values_mean_leagues_own(self):
        self.assertEqual(lust_wallpaper.clean(None), {"league": True, "name": "", "rev": 0})
        self.assertEqual(lust_wallpaper.clean({"name": 3, "rev": True}), {"league": True, "name": "", "rev": 0})

    def test_a_named_file(self):
        self.assertEqual(lust_wallpaper.clean({"name": "a.jpg", "rev": 4}), {"league": False, "name": "a.jpg", "rev": 4})

    def test_videos(self):
        self.assertFalse(lust_wallpaper.is_video("a.JPG"))
        self.assertTrue(lust_wallpaper.is_video("b.webm"))


class BridgeTests(unittest.TestCase):
    def tearDown(self):
        lust_wallpaper._reported.clear()

    def test_state_is_remembered(self):
        reply = lust_wallpaper.bridge_reply({"action": "state", "league": False, "name": "a.jpg"})
        self.assertEqual(reply["action"], "noted")
        self.assertEqual(lust_wallpaper.current(), {"league": False, "name": "a.jpg"})

    def test_get_sends_the_saved_choice(self):
        saved = {"league": False, "name": "a.jpg", "rev": 2}
        with mock.patch.object(lust_wallpaper, "choice", return_value=saved):
            reply = lust_wallpaper.bridge_reply({"action": "get"})
        self.assertEqual(reply, {"type": "lust-wallpaper", "action": "apply", **saved})

    def test_get_without_a_choice(self):
        with mock.patch.object(lust_wallpaper, "choice", return_value=None):
            self.assertEqual(lust_wallpaper.bridge_reply({"action": "get"})["action"], "none")

    def test_choosing_an_unknown_file(self):
        with mock.patch.object(lust_wallpaper, "files", return_value=["a.jpg"]):
            self.assertEqual(lust_wallpaper.choose("b.jpg"), "Bu duvar kağıdı bulunamadı")


if __name__ == "__main__":
    unittest.main()
