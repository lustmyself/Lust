import unittest

from launcher import lust_hero


class RankTextTests(unittest.TestCase):
    def test_divisions_and_apex_tiers(self):
        self.assertEqual(lust_hero._rank_text({"tier": "GOLD", "division": "II", "leaguePoints": 40}), "Altın II · 40 LP")
        self.assertEqual(lust_hero._rank_text({"tier": "GRANDMASTER", "division": "I", "leaguePoints": 1104}),
                         "Büyük Usta · 1104 LP")

    def test_unranked(self):
        self.assertEqual(lust_hero._rank_text({}), "Derecesiz")
        self.assertEqual(lust_hero._rank_text({"tier": "NONE"}), "Derecesiz")

    def test_refresh_without_client(self):
        from unittest import mock
        with mock.patch("launcher.lust_offline._lcu_credentials", return_value=None):
            self.assertFalse(lust_hero.refresh())


if __name__ == "__main__":
    unittest.main()
