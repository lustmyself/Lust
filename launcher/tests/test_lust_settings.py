import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from launcher import lust_settings


class SettingsTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.patches = [
            mock.patch("utils.core.paths.get_user_data_dir", return_value=Path(self.folder.name)),
            mock.patch.object(lust_settings, "_cache", None),
        ]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        self.folder.cleanup()

    def test_defaults_keep_lust_working(self):
        self.assertTrue(lust_settings.enabled("skins"))
        self.assertTrue(lust_settings.enabled("custom_skins"))
        self.assertFalse(lust_settings.enabled("quiet_start"))
        self.assertEqual(lust_settings.get("backdrop"), "cinematic")
        self.assertTrue(lust_settings.enabled("something_unknown"))

    def test_saved_and_read_back(self):
        self.assertTrue(lust_settings.set_value("skins", False))
        self.assertTrue(lust_settings.set_value("backdrop", "hextech"))
        saved = json.loads((Path(self.folder.name) / lust_settings.FILE).read_text(encoding="utf-8"))
        self.assertEqual((saved["skins"], saved["backdrop"]), (False, "hextech"))
        with mock.patch.object(lust_settings, "_cache", None):
            self.assertFalse(lust_settings.enabled("skins"))

    def test_only_offered_values(self):
        self.assertFalse(lust_settings.set_value("nope", True))
        self.assertFalse(lust_settings.set_value("skins", "yes"))
        self.assertFalse(lust_settings.set_value("backdrop", "pink"))

    def test_a_broken_file_falls_back_to_defaults(self):
        (Path(self.folder.name) / lust_settings.FILE).write_text('{"skins": "off", "backdrop": 3', encoding="utf-8")
        self.assertTrue(lust_settings.enabled("skins"))
        (Path(self.folder.name) / lust_settings.FILE).write_text('{"skins": "off"}', encoding="utf-8")
        with mock.patch.object(lust_settings, "_cache", None):
            self.assertTrue(lust_settings.enabled("skins"))


class SwitchesTests(unittest.TestCase):
    def test_custom_skins_switch(self):
        from pengu.communication import lust_custom_skins
        state = {"a.zip": {"enabled": True, "championId": 103}}
        with mock.patch.object(lust_custom_skins, "_load", return_value=state), \
                mock.patch.object(lust_custom_skins, "folder") as folder:
            folder.return_value.__truediv__.return_value.is_file.return_value = True
            folder.return_value.__truediv__.return_value.stem = "a"
            with mock.patch.object(lust_settings, "enabled", return_value=False):
                self.assertIsNone(lust_custom_skins.custom_mod_for(103, 103000))
            with mock.patch.object(lust_settings, "enabled", return_value=True):
                self.assertIsNotNone(lust_custom_skins.custom_mod_for(103, 103000))

    def test_hub_action_saves_and_answers(self):
        from launcher import lust_hub
        with mock.patch.object(lust_settings, "set_value", return_value=True) as save:
            self.assertIn("modsuz", lust_hub._set_setting({"key": "skins", "value": False}))
        save.assert_called_once_with("skins", False)
        with mock.patch.object(lust_settings, "set_value", return_value=False):
            self.assertTrue(lust_hub._set_setting({"key": "x", "value": 1}))


if __name__ == "__main__":
    unittest.main()
