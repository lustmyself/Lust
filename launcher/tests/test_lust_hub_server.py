import http.client
import json
import unittest
from unittest.mock import patch

from launcher import lust_hub, lust_hub_server as server
from launcher.lust_hub_shell import main_if_window


def _request(method, path, token=None, host=None, body=None):
    conn = http.client.HTTPConnection("127.0.0.1", server._port, timeout=5)
    headers = {"Host": host or f"127.0.0.1:{server._port}"}
    if token is not None:
        headers["X-Lust-Hub"] = token
    conn.request(method, path, body=json.dumps(body) if body is not None else None, headers=headers)
    response = conn.getresponse()
    data = response.read()
    conn.close()
    return response.status, data


class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        assert server.start()

    def test_page_carries_the_token_and_every_theme(self):
        status, body = _request("GET", "/")
        self.assertEqual(status, 200)
        self.assertIn(json.dumps(server._token).encode(), body)
        self.assertIn(b'"luminous"', body)
        self.assertNotIn(b"__TOKEN__", body)

    def test_other_hosts_are_refused(self):
        self.assertEqual(_request("GET", "/", host="evil.example")[0], 403)
        self.assertEqual(_request("GET", "/api/state", token=server._token, host="evil.example")[0], 403)

    def test_api_needs_the_token(self):
        self.assertEqual(_request("GET", "/api/state")[0], 403)
        self.assertEqual(_request("POST", "/api/action/quit", token="wrong", body={})[0], 403)

    def test_state_and_actions_with_the_token(self):
        with patch.object(lust_hub, "snapshot", return_value={"phase": "ready"}):
            status, body = _request("GET", "/api/state", token=server._token)
        self.assertEqual((status, json.loads(body)), (200, {"phase": "ready"}))
        self.assertTrue(server.page_open())
        with patch.object(lust_hub, "run_action") as run:
            self.assertEqual(_request("POST", "/api/action/autostart", token=server._token, body={"x": 1})[0], 200)
            self.assertEqual(_request("POST", "/api/action/nope", token=server._token, body={})[0], 404)
        run.assert_called_once()

    def test_previews_only_for_known_themes(self):
        self.assertEqual(_request("GET", "/preview/..%2fsecret.png")[0], 404)


class ShellArgTests(unittest.TestCase):
    def test_only_runs_for_its_argument_and_local_urls(self):
        self.assertFalse(main_if_window(["Lust.exe"]))
        with patch("launcher.lust_hub_shell.run") as run:
            self.assertTrue(main_if_window(["Lust.exe", "--lust-hub-window", "https://evil.example/"]))
            run.assert_not_called()
            self.assertTrue(main_if_window(["Lust.exe", "--lust-hub-window", "http://127.0.0.1:47823/"]))
            run.assert_called_once_with("http://127.0.0.1:47823/", 0)


if __name__ == "__main__":
    unittest.main()
