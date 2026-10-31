import unittest
from unittest import mock
from urllib.parse import parse_qs, urlparse

from launcher import lust_discord


class LoginTests(unittest.TestCase):
    def setUp(self):
        lust_discord._pending.clear()

    def test_the_link_comes_back_to_this_hub(self):
        link = lust_discord.login_url(47824)
        query = parse_qs(urlparse(link).query)
        self.assertEqual(query["redirect_uri"], ["http://127.0.0.1:47824/discord"])
        self.assertEqual(query["scope"], ["identify"])
        self.assertIn(query["state"][0], lust_discord._pending)

    def test_no_link_without_the_application(self):
        with mock.patch.object(lust_discord, "CLIENT_ID", ""):
            self.assertIsNone(lust_discord.login_url(47823))

    def test_an_unknown_state_is_refused_without_asking_discord(self):
        with mock.patch("requests.get") as get:
            self.assertIn("süresi doldu", lust_discord.finish("token", "made-up"))
        get.assert_not_called()

    def test_a_state_works_once(self):
        state = parse_qs(urlparse(lust_discord.login_url(47823)).query)["state"][0]
        self.assertTrue(lust_discord._take_state(state))
        self.assertFalse(lust_discord._take_state(state))


if __name__ == "__main__":
    unittest.main()
