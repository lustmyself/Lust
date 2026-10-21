import unittest

from launcher import lust_hero


class RankTextTests(unittest.TestCase):
    def test_divisions_and_apex_tiers(self):
        self.assertEqual(lust_hero._rank_text({"tier": "GOLD", "division": "II", "leaguePoints": 40}), "Altın II · 40 LP")
        self.assertEqual(lust_hero._rank_text({"tier": "GRANDMASTER", "division": "I", "leaguePoints": 1104}),
                         "Üstatlık · 1104 LP")

    def test_unranked(self):
        self.assertEqual(lust_hero._rank_text({}), "Derecesiz")
        self.assertEqual(lust_hero._rank_text({"tier": "NONE"}), "Derecesiz")

    def test_refresh_without_client(self):
        from unittest import mock
        with mock.patch("launcher.lust_offline._lcu_credentials", return_value=None):
            self.assertFalse(lust_hero.refresh())


class CutoffTests(unittest.TestCase):
    def test_parse_keeps_fresh_servers(self):
        import time
        now = int(time.time() * 1000)
        page = (f'[{{"region":"TR1","challenger":1256,"grandmaster":784,"timeFetched":{now}}},'
                f'{{"region":"PH2","challenger":500,"grandmaster":200,"timeFetched":1738093826907}}]')
        self.assertEqual(lust_hero.parse_cutoffs(page), {"TR1": {"challenger": 1256, "grandmaster": 784}})
        escaped = page.replace('"', '\\"')
        self.assertEqual(lust_hero.parse_cutoffs(escaped), {"TR1": {"challenger": 1256, "grandmaster": 784}})

    def test_client_region_maps_to_server(self):
        from unittest import mock
        with mock.patch.object(lust_hero, "_cutoffs", {"TR1": {"challenger": 1256, "grandmaster": 784}}),                 mock.patch.object(lust_hero, "_cutoffs_at", 1e18):
            self.assertEqual(lust_hero.cutoffs_for("TR"), {"challenger": 1256, "grandmaster": 784, "region": "TR"})
            self.assertIsNone(lust_hero.cutoffs_for("EUW"))


class SavedCardTests(unittest.TestCase):
    def test_a_missed_read_is_tried_again(self):
        import tempfile
        from pathlib import Path
        from unittest import mock
        with tempfile.TemporaryDirectory() as folder, mock.patch.object(lust_hero, "_dir", return_value=Path(folder)),                 mock.patch.object(lust_hero, "_data", None):
            self.assertIsNone(lust_hero.get())
            (Path(folder) / "hero.json").write_text('{"name": "Lust"}', encoding="utf-8")
            self.assertEqual(lust_hero.get(), {"name": "Lust"})


if __name__ == "__main__":
    unittest.main()
