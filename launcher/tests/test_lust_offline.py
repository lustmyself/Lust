import tempfile
import time
import unittest
from pathlib import Path
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


class LocalhostResolutionTests(unittest.TestCase):
    def _run(self, hosts_text, resolves):
        with tempfile.TemporaryDirectory() as tmp:
            hosts = Path(tmp) / "hosts"
            if hosts_text is not None:
                hosts.write_text(hosts_text, encoding="utf-8")
            with patch.object(lust_offline, "_hosts_file", return_value=hosts), \
                 patch.object(lust_offline, "_resolves_to_loopback", return_value=resolves), \
                 patch.object(lust_offline.subprocess, "run") as run:
                ok = lust_offline.ensure_localhost_resolution()
            return ok, (hosts.read_text(encoding="utf-8") if hosts.exists() else None), run

    def test_entry_added_when_dns_fails(self):
        ok, text, run = self._run("# hosts\n127.0.0.1 localhost", resolves=False)
        self.assertTrue(ok)
        self.assertEqual(text, "# hosts\n127.0.0.1 localhost\n127.0.0.1 deceive-localhost.molenzwiebel.xyz  # Lust Offline\n")
        run.assert_called_once()

    def test_nothing_written_when_dns_works(self):
        ok, text, run = self._run("# hosts\n", resolves=True)
        self.assertTrue(ok)
        self.assertEqual(text, "# hosts\n")
        run.assert_not_called()

    def test_existing_entry_is_kept_once(self):
        original = "127.0.0.1   Deceive-Localhost.molenzwiebel.xyz\n"
        ok, text, _ = self._run(original, resolves=False)
        self.assertTrue(ok)
        self.assertEqual(text, original)

    def test_commented_entry_does_not_count(self):
        _, text, _ = self._run("# 127.0.0.1 deceive-localhost.molenzwiebel.xyz\n", resolves=False)
        self.assertEqual(text.count("deceive-localhost"), 2)
