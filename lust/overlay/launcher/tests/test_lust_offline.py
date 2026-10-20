import time
import unittest
from unittest.mock import MagicMock, patch

from launcher import lust_offline


def _proc(name, args=(), age=600.0):
    proc = MagicMock()
    proc.info = {"name": name}
    proc.cmdline.return_value = [name, *args]
    proc.create_time.return_value = time.time() - age
    return proc


class LeagueWithoutProxyTests(unittest.TestCase):
    def _check(self, *procs):
        with patch.object(lust_offline.psutil, "process_iter", return_value=list(procs)):
            return lust_offline.league_without_proxy()

    def test_league_shortcut_without_proxy_is_restarted(self):
        self.assertTrue(self._check(_proc("RiotClientServices.exe", ["--launch-product=league_of_legends"])))

    def test_client_already_behind_the_proxy_is_left_alone(self):
        self.assertFalse(self._check(_proc(
            "RiotClientServices.exe",
            ["--client-config-url=http://127.0.0.1:5000", "--launch-product=league_of_legends"],
        )))
        self.assertFalse(self._check(
            _proc("RiotClientServices.exe", ["--launch-product=league_of_legends"]),
            _proc("LustOffline.exe"),
        ))

    def test_running_game_and_other_games_are_left_alone(self):
        self.assertFalse(self._check(
            _proc("RiotClientServices.exe", ["--launch-product=league_of_legends"]),
            _proc("League of Legends.exe"),
        ))
        self.assertFalse(self._check(_proc("RiotClientServices.exe", ["--launch-product=valorant"])))
        self.assertFalse(self._check(_proc("RiotClientServices.exe")))

    def test_play_pressed_in_an_open_riot_client(self):
        self.assertTrue(self._check(_proc("RiotClientServices.exe"), _proc("LeagueClient.exe", age=3)))
        # A League client that has been open for a while is not restarted
        self.assertFalse(self._check(_proc("RiotClientServices.exe"), _proc("LeagueClient.exe", age=600)))


if __name__ == "__main__":
    unittest.main()
