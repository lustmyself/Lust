import base64
import json
import tempfile
import time
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from pengu.communication import lust_custom_skins as skins


def _fantome(path: Path, champion: str = "Ahri", title: str = "Arcade Ahri") -> Path:
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("META/info.json", json.dumps({"Name": title, "Author": "x"}))
        archive.writestr(f"WAD/{champion}.wad.client/data/characters/{champion.lower()}/skin0.bin", b"x")
    return path


class CustomSkinsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        patcher = patch.object(skins, "get_user_data_dir", return_value=self.root)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self.tmp.cleanup)
        self.build = int(time.time())
        patcher = patch.object(skins, "game_build", side_effect=lambda: self.build)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_lists_mod_files_with_their_champion_wad_and_title(self):
        _fantome(skins.folder() / "arcade.fantome")
        (skins.folder() / "notes.txt").write_text("not a mod")
        listed = skins.list_skins()
        self.assertEqual(len(listed), 1)
        self.assertEqual(listed[0]["name"], "arcade.fantome")
        self.assertEqual(listed[0]["title"], "Arcade Ahri")
        self.assertEqual(listed[0]["wads"], ["ahri"])
        self.assertFalse(listed[0]["enabled"])

    def test_broken_file_is_listed_as_broken(self):
        (skins.folder() / "broken.zip").write_bytes(b"not a zip")
        self.assertTrue(skins.list_skins()[0]["broken"])

    def test_needs_a_champion_before_it_can_be_switched_on(self):
        _fantome(skins.folder() / "a.fantome")
        self.assertEqual(skins.handle({"action": "set", "name": "a.fantome", "enabled": True})["error"],
                         "pick a champion first")

    def test_one_skin_per_champion_is_on(self):
        _fantome(skins.folder() / "a.fantome")
        _fantome(skins.folder() / "b.zip")
        for name in ("a.fantome", "b.zip"):
            skins.handle({"action": "set", "name": name, "championId": 103})
        skins.handle({"action": "set", "name": "a.fantome", "enabled": True})
        reply = skins.handle({"action": "set", "name": "b.zip", "enabled": True})
        state = {s["name"]: s["enabled"] for s in reply["skins"]}
        self.assertEqual(state, {"a.fantome": False, "b.zip": True})

    def test_plays_only_on_the_champions_default_skin(self):
        _fantome(skins.folder() / "a.fantome")
        skins.handle({"action": "set", "name": "a.fantome", "championId": 103})
        self.assertIsNone(skins.custom_mod_for(103, 103000))  # still off
        skins.handle({"action": "set", "name": "a.fantome", "enabled": True})
        mod = skins.custom_mod_for(103, 103000)
        self.assertEqual(mod["champion_id"], 103)
        self.assertEqual(mod["skin_id"], 103000)
        self.assertEqual(Path(mod["mod_path"]).name, "a.fantome")
        self.assertIsNone(mod["relative_path"])
        self.assertEqual(skins.custom_mod_for(103, 103001)["skin_id"], 103001)  # on the skin picked
        self.assertIsNone(skins.custom_mod_for(103, 84001))  # a skin of another champion
        self.assertIsNone(skins.custom_mod_for(84, 84000))  # another champion

    def test_changing_the_champion_switches_it_off_and_stops_guessing(self):
        _fantome(skins.folder() / "a.fantome")
        skins.handle({"action": "set", "name": "a.fantome", "championId": 103})
        skins.handle({"action": "set", "name": "a.fantome", "enabled": True})
        skin = skins.handle({"action": "set", "name": "a.fantome", "championId": 0})["skins"][0]
        self.assertIsNone(skin["championId"])
        self.assertFalse(skin["enabled"])
        self.assertFalse(skin["auto"])
        self.assertIsNone(skins.custom_mod_for(103, 103000))

    def test_a_skin_that_keeps_crashing_the_game_is_switched_off(self):
        _fantome(skins.folder() / "a.fantome")
        skins.handle({"action": "set", "name": "a.fantome", "championId": 103})
        skins.handle({"action": "set", "name": "a.fantome", "enabled": True})
        self.assertIsNotNone(skins.custom_mod_for(103, 103000))
        with patch("utils.core.issue_reporter.report_issue") as report, \
                patch("launcher.lust_hub.toast") as toast:
            skins.game_keeps_crashing()
        self.assertFalse(skins.list_skins()[0]["enabled"])
        self.assertIn("Arcade Ahri", toast.call_args.args[0])
        self.assertEqual(report.call_args.args[0], "LUST_MOD_CRASH")
        self.assertIsNone(skins.custom_mod_for(103, 103000))

    def _play(self, name="a.fantome"):
        skins.handle({"action": "set", "name": name, "championId": 103})
        skins.handle({"action": "set", "name": name, "enabled": True})
        self.assertIsNotNone(skins.custom_mod_for(103, 103000))

    def test_patch_status_follows_games_played(self):
        _fantome(skins.folder() / "a.fantome")
        self.assertEqual(skins.list_skins()[0]["status"], "new")
        self._play()
        skins.game_ran_fine()
        self.assertEqual(skins.list_skins()[0]["status"], "ok")
        self.build += 1  # League updated
        self.assertEqual(skins.list_skins()[0]["status"], "untested")
        self.assertIsNotNone(skins.custom_mod_for(103, 103000))
        with patch("utils.core.issue_reporter.report_issue"), patch("launcher.lust_hub.toast"):
            skins.game_keeps_crashing()
        listed = skins.list_skins()[0]
        self.assertEqual((listed["status"], listed["enabled"]), ("crashed", False))
        self.build += 1  # crashed on the patch before: not known for this one
        self.assertEqual(skins.list_skins()[0]["status"], "untested")

    def _bundled(self, fresh):
        asset = self.root / "asset.modpkg"
        asset.write_bytes(b"x")
        if not fresh:
            (self.root / "lust_fonts.json").write_text("{}")
        with patch("utils.core.paths.get_asset_path", return_value=asset):
            skins.ensure_default()
            skins.ensure_default()

    def test_a_fresh_install_gets_the_talon_skin_switched_on(self):
        self._bundled(fresh=True)
        state = skins._load()[skins.DEFAULT_SKIN]
        self.assertEqual((state["championId"], state["enabled"]), (91, True))
        self.assertTrue((skins.folder() / skins.DEFAULT_SKIN).is_file())

    def test_an_update_leaves_custom_skins_alone(self):
        self._bundled(fresh=False)
        self.assertFalse((skins.folder() / skins.DEFAULT_SKIN).exists())

    def test_a_game_without_the_skin_does_not_blame_it(self):
        _fantome(skins.folder() / "a.fantome")
        self._play()
        self.assertIsNone(skins.custom_mod_for(266, 266000))  # next game, another champion
        with patch("utils.core.issue_reporter.report_issue"), patch("launcher.lust_hub.toast"):
            skins.game_keeps_crashing()
        self.assertTrue(skins.list_skins()[0]["enabled"])

    def test_skin_packed_long_before_the_patch_looks_old(self):
        _fantome(skins.folder() / "a.fantome")  # packed now
        self.assertEqual(skins.list_skins()[0]["status"], "new")
        self.assertIsInstance(skins.list_skins()[0]["made"], int)
        self.build = skins.list_skins()[0]["made"] + skins.OLD_AFTER_S + 1
        self.assertEqual(skins.list_skins()[0]["status"], "old")

    def test_removed_file_stops_playing(self):
        _fantome(skins.folder() / "a.fantome")
        skins.handle({"action": "set", "name": "a.fantome", "championId": 103})
        skins.handle({"action": "set", "name": "a.fantome", "enabled": True})
        (skins.folder() / "a.fantome").unlink()
        self.assertIsNone(skins.custom_mod_for(103, 103000))
        self.assertEqual(skins.list_skins(), [])

    def test_dropped_file_arrives_in_chunks(self):
        data = (skins.folder() / "src.zip")
        _fantome(data)
        raw = data.read_bytes()
        data.unlink()
        half = len(raw) // 2
        for index, part in enumerate((raw[:half], raw[half:])):
            reply = skins.handle({"action": "chunk", "name": "dropped.zip", "index": index, "total": 2,
                                  "data": base64.b64encode(part).decode()})
            self.assertEqual(reply["error"], "")
        self.assertEqual((skins.folder() / "dropped.zip").read_bytes(), raw)

    def test_bad_names_are_refused(self):
        for name in ("../evil.zip", "x.exe", ".hidden.zip", "a/b.zip"):
            reply = skins.handle({"action": "chunk", "name": name, "index": 0, "total": 1, "data": ""})
            self.assertTrue(reply["error"], name)
        self.assertEqual(skins.handle({"action": "set", "name": "../x.zip", "championId": 1})["error"], "file is gone")


if __name__ == "__main__":
    unittest.main()
