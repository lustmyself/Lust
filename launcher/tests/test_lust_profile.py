import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from launcher import lust_profile

AHRI = {
    "id": 103,
    "name": "Ahri",
    "skins": [
        {"id": 103000, "isBase": True, "name": "Ahri",
         "tilePath": "/lol-game-data/assets/ASSETS/Characters/Ahri/Skins/Base/Images/ahri_splash_tile_0.jpg",
         "uncenteredSplashPath": "/lol-game-data/assets/ASSETS/Characters/Ahri/Skins/Base/Images/ahri_splash_uncentered_0.jpg"},
        {"id": 103001, "isBase": False, "name": "Dynasty Ahri",
         "splashPath": "/lol-game-data/assets/v1/champion-splashes/103/103001.jpg"},
        {"id": 103086, "isBase": False, "name": "Risen Legend Ahri",
         "questSkinInfo": {"tiers": [{"id": 103086, "name": "Risen Legend Ahri"},
                                     {"id": 103087, "name": "Immortalized Legend Ahri"}]}},
        {"id": "bad", "name": "Bad"},
        "junk",
    ],
}


class ProfileTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.folder = Path(tmp.name)
        p = patch.object(lust_profile, "_pending_path", return_value=self.folder / lust_profile.PENDING_FILE)
        p.start()
        self.addCleanup(p.stop)
        p = patch.object(lust_profile, "skins", return_value=lust_profile.clean_skins(AHRI))
        p.start()
        self.addCleanup(p.stop)

    def test_skins_list_base_first_with_tiers_and_cdragon_images(self):
        skins = lust_profile.clean_skins(AHRI)
        self.assertEqual([s["id"] for s in skins], [103000, 103001, 103086, 103087])
        self.assertTrue(skins[0]["base"])
        self.assertEqual(skins[0]["tile"], lust_profile.CDRAGON
                         + "assets/characters/ahri/skins/base/images/ahri_splash_tile_0.jpg")
        self.assertTrue(skins[1]["splash"].endswith("v1/champion-splashes/103/103001.jpg"))
        self.assertEqual(skins[3]["name"], "Immortalized Legend Ahri")
        self.assertEqual(lust_profile.clean_skins("nope"), [])

    def test_asset_url_ignores_other_paths(self):
        self.assertEqual(lust_profile.asset_url("https://example.com/x.jpg"), "")
        self.assertEqual(lust_profile.asset_url(None), "")

    def test_skin_by_id(self):
        self.assertEqual(lust_profile.skin(103001)["name"], "Dynasty Ahri")
        self.assertIsNone(lust_profile.skin("x"))
        self.assertIsNone(lust_profile.skin(0))

    def test_set_while_client_runs_posts_the_skin(self):
        with patch("launcher.lust_offline._lcu_credentials", return_value=(1234, "t")), \
                patch.object(lust_profile, "_lcu", return_value={}) as lcu:
            message = lust_profile.set_background(103001)
        lcu.assert_called_once_with("POST", lust_profile.PROFILE_PATH, {"key": "backgroundSkinId", "value": 103001})
        self.assertIn("Dynasty Ahri", message)
        self.assertEqual(lust_profile.pending(), 0)

    def test_set_while_client_closed_waits_and_applies_later(self):
        with patch("launcher.lust_offline._lcu_credentials", return_value=None):
            message = lust_profile.set_background(103001)
        self.assertIn("LoL açılınca", message)
        self.assertEqual(lust_profile.pending(), 103001)
        with patch.object(lust_profile, "_lcu", return_value=None):
            lust_profile.apply_pending()
        self.assertEqual(lust_profile.pending(), 103001)  # client still not answering
        with patch.object(lust_profile, "_lcu", return_value={}) as lcu:
            lust_profile.apply_pending()
        lcu.assert_called_once()
        self.assertEqual(lust_profile.pending(), 0)

    def test_client_refusing_keeps_nothing_pending(self):
        with patch("launcher.lust_offline._lcu_credentials", return_value=(1234, "t")), \
                patch.object(lust_profile, "_lcu", return_value=None):
            message = lust_profile.set_background(103001)
        self.assertIn("tekrar", message)
        self.assertEqual(lust_profile.pending(), 0)

    def test_bad_ids_do_nothing(self):
        with patch.object(lust_profile, "_lcu") as lcu:
            self.assertEqual(lust_profile.set_background("x"), "")
            self.assertEqual(lust_profile.set_background(-5), "")
        lcu.assert_not_called()

    def test_listing_shows_pending_choice_over_client(self):
        (self.folder / lust_profile.PENDING_FILE).write_text(json.dumps({"pending": 103087}), encoding="utf-8")
        with patch.object(lust_profile, "current", return_value=None), \
                patch("launcher.lust_skins.champions", return_value=[{"id": 103, "name": "Ahri", "alias": "ahri"}]):
            data = lust_profile.listing()
        self.assertEqual(data["current"], 103087)
        self.assertTrue(data["pending"])
        self.assertFalse(data["online"])
        self.assertEqual(data["skin"]["name"], "Immortalized Legend Ahri")
        self.assertEqual(data["champions"], [{"id": 103, "name": "Ahri"}])


if __name__ == "__main__":
    unittest.main()
