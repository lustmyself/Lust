import unittest
from unittest import mock

from launcher import lust_media


class ControlTests(unittest.TestCase):
    def test_only_known_controls_are_queued(self):
        with mock.patch.object(lust_media, "watch"), mock.patch.object(lust_media, "_pending", []) as pending:
            self.assertTrue(lust_media.control("play_pause"))
            self.assertTrue(lust_media.control("mute"))
            self.assertFalse(lust_media.control("delete_everything"))
            self.assertEqual(pending, ["play_pause", "mute"])

    def test_reading_starts_when_the_page_asks(self):
        with mock.patch.object(lust_media, "_thread", None), \
                mock.patch.object(lust_media.threading, "Thread") as thread:
            lust_media.watch()
        thread.assert_called_once()
        self.assertGreater(lust_media._wanted_until, 0)

    def test_nothing_plays_without_a_session(self):
        import asyncio

        async def no_session():
            return None

        with mock.patch.object(lust_media, "_session", no_session):
            loop = asyncio.new_event_loop()
            self.assertEqual(loop.run_until_complete(lust_media._read_info("x")), "")
            loop.close()
        self.assertFalse(lust_media._state["available"])


class ServerRouteTests(unittest.TestCase):
    def test_media_needs_the_token(self):
        import json
        from launcher import lust_hub_server as server
        from launcher.tests.test_lust_hub_server import _request
        server.start()
        self.assertEqual(_request("GET", "/api/media")[0], 403)
        self.assertEqual(_request("POST", "/api/media/next", token="wrong", body={})[0], 403)
        with mock.patch.object(lust_media, "state", return_value={"available": False}):
            status, body = _request("GET", "/api/media", token=server._token)
        self.assertEqual((status, json.loads(body)), (200, {"available": False}))
        with mock.patch.object(lust_media, "control", return_value=False):
            self.assertEqual(_request("POST", "/api/media/nope", token=server._token, body={})[0], 404)


if __name__ == "__main__":
    unittest.main()
