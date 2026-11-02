import json
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


class UserTests(unittest.TestCase):
    def setUp(self):
        import tempfile
        from pathlib import Path
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.dir = Path(self.folder.name)
        patcher = mock.patch.object(lust_discord, "_dir", return_value=self.dir)
        patcher.start()
        self.addCleanup(patcher.stop)

    def _write(self, data):
        (self.dir / lust_discord.FILE).write_text(json.dumps(data), encoding="utf-8")
        (self.dir / lust_discord.AVATAR).write_bytes(b"png")

    def test_an_old_sign_in_is_signed_out_once(self):
        self._write({"id": "80351110224678912", "name": "Bugra", "username": "bugra"})
        self.assertIsNone(lust_discord.user())
        self.assertFalse((self.dir / lust_discord.FILE).exists())
        self.assertFalse((self.dir / lust_discord.AVATAR).exists())

    def test_a_new_sign_in_shows_the_picture(self):
        self._write({"id": "80351110224678912", "name": "Bugra", "username": "bugra",
                     "avatar_hash": "8342729096ea3675442027381ff50dfe"})
        me = lust_discord.user()
        self.assertEqual(me["name"], "Bugra")
        self.assertEqual(me["avatar_url"], "https://cdn.discordapp.com/avatars/80351110224678912/"
                                           "8342729096ea3675442027381ff50dfe.png?size=64")

    def test_no_picture_on_discord_stays_signed_in(self):
        self._write({"id": "80351110224678912", "name": "Bugra", "username": "bugra", "avatar_hash": ""})
        self.assertTrue(lust_discord.user()["avatar_url"].startswith("https://cdn.discordapp.com/embed/avatars/"))


if __name__ == "__main__":
    unittest.main()
