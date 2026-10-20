import unittest
from unittest.mock import MagicMock

from lcu.features.lobby_reveal import (
    RevealedPlayer,
    apply_champ_select_session,
    build_opgg_multi_url,
    build_opgg_profile_url,
    build_porofessor_url,
    build_ugg_multi_url,
    build_ugg_profile_url,
    opgg_region,
    parse_participants,
    parse_riotclient_args,
    porofessor_region,
    riot_platform,
)
from threads.core.lobby_reveal_thread import LobbyRevealThread


def _chat(*players):
    return {"participants": [
        {"cid": cid, "game_name": name, "game_tag": tag, "puuid": puuid}
        for cid, name, tag, puuid in players
    ]}


class RiotClientArgsTests(unittest.TestCase):
    def test_reads_port_and_token_in_both_forms(self):
        creds = parse_riotclient_args([
            "LeagueClientUx.exe", "--riotclient-auth-token=abc", "--riotclient-app-port", "51234",
        ])
        self.assertEqual((creds.port, creds.token), (51234, "abc"))

    def test_rejects_missing_or_bad_port(self):
        self.assertIsNone(parse_riotclient_args(["--riotclient-auth-token=abc"]))
        self.assertIsNone(parse_riotclient_args(["--riotclient-auth-token=abc", "--riotclient-app-port=0"]))
        self.assertIsNone(parse_riotclient_args(["--riotclient-app-port=123"]))


class ParticipantTests(unittest.TestCase):
    def test_keeps_only_champ_select_participants(self):
        players = parse_participants(_chat(
            ("abc@champ-select.eu1.pvp.net", "One", "EUW", "p1"),
            ("abc@lol-post-game.eu1.pvp.net", "Other", "EUW", "p2"),
            ("abc@champ-select.eu1.pvp.net", "", "EUW", "p3"),
        ))
        self.assertEqual([p.riot_id for p in players], ["One#EUW"])

    def test_handles_missing_data(self):
        self.assertEqual(parse_participants(None), [])
        self.assertEqual(parse_participants({}), [])

    def test_session_adds_roles_and_sorts_by_pick_turn(self):
        players = parse_participants(_chat(
            ("x@champ-select", "Late", "1", "p1"),
            ("x@champ-select", "Early", "2", "p2"),
            ("x@champ-select", "ChatOnly", "3", "p3"),
        ))
        apply_champ_select_session(players, {"myTeam": [
            {"puuid": "p1", "assignedPosition": "UTILITY", "cellId": 4, "pickTurn": 2},
            {"puuid": "p2", "assignedPosition": "top", "cellId": 0, "pickTurn": 1},
        ]})
        self.assertEqual([p.game_name for p in players], ["Early", "Late", "ChatOnly"])
        self.assertEqual([p.position for p in players], ["top", "utility", ""])


class OpggLinkTests(unittest.TestCase):
    def test_region_aliases(self):
        self.assertEqual(opgg_region("EUW"), "euw")
        self.assertEqual(opgg_region("SG2"), "sg")
        self.assertEqual(opgg_region(None), "")

    def test_multi_search_url_encodes_riot_ids(self):
        players = [RevealedPlayer("Player One", "NA1"), RevealedPlayer("Şeker", "TR1")]
        self.assertEqual(
            build_opgg_multi_url(players, "tr"),
            "https://www.op.gg/multisearch/tr?summoners=Player%20One%23NA1%2C%C5%9Eeker%23TR1",
        )
        self.assertEqual(build_opgg_multi_url([], "tr"), "")
        self.assertEqual(build_opgg_multi_url(players, ""), "")

    def test_profile_url(self):
        self.assertEqual(
            build_opgg_profile_url(RevealedPlayer("Player One", "NA1"), "na"),
            "https://www.op.gg/summoners/na/Player%20One-NA1",
        )


class UggLinkTests(unittest.TestCase):
    def test_platform_ids(self):
        self.assertEqual(riot_platform("EUW"), "euw1")
        self.assertEqual(riot_platform("LAS"), "la2")
        self.assertEqual(riot_platform("KR"), "kr")
        self.assertEqual(riot_platform("EUW1"), "euw1")
        self.assertEqual(riot_platform(None), "")

    def test_multi_and_profile_urls(self):
        players = [RevealedPlayer("Player One", "NA1"), RevealedPlayer("Two", "EUW")]
        self.assertEqual(
            build_ugg_multi_url(players, "na1"),
            "https://u.gg/lol/multisearch?region=na1&summoners=Player%20One-NA1%2CTwo-EUW",
        )
        self.assertEqual(build_ugg_multi_url(players, ""), "")
        self.assertEqual(
            build_ugg_profile_url(players[0], "na1"),
            "https://u.gg/lol/profile/na1/Player%20One-NA1/overview",
        )


class PorofessorLinkTests(unittest.TestCase):
    def test_region_slugs(self):
        self.assertEqual(porofessor_region("EUW"), "euw")
        self.assertEqual(porofessor_region("LA2"), "las")
        self.assertEqual(porofessor_region("OC1"), "oce")
        self.assertEqual(porofessor_region(None), "")

    def test_pregame_url_lists_the_team(self):
        players = [RevealedPlayer("Player One", "NA1"), RevealedPlayer("Second Player", "0911")]
        self.assertEqual(
            build_porofessor_url(players, "na"),
            "https://porofessor.gg/pregame/na/Player%20One-NA1,Second%20Player-0911",
        )
        self.assertEqual(build_porofessor_url([], "na"), "")
        self.assertEqual(build_porofessor_url(players, ""), "")


class LobbyRevealThreadTests(unittest.TestCase):
    def _thread(self, phase):
        lcu = MagicMock(ok=True, region_locale={"webRegion": "EUW"}, session={"myTeam": []})
        state = MagicMock(phase=phase)
        broadcaster = state.ui_skin_thread.broadcaster
        thread = LobbyRevealThread(lcu, state)
        thread.chat = MagicMock()
        thread.chat.get_participants.return_value = _chat(("x@champ-select", "One", "EUW", "p1"))
        return thread, state, broadcaster

    def test_sends_team_in_champ_select_then_clears_after(self):
        thread, state, broadcaster = self._thread("ChampSelect")
        thread._tick()
        payload = broadcaster.broadcast_lobby_reveal.call_args[0][0]
        self.assertTrue(payload["active"])
        self.assertEqual(payload["players"][0]["riotId"], "One#EUW")
        self.assertEqual(payload["players"][0]["puuid"], "p1")
        self.assertEqual(payload["players"][0]["poroUrl"], "https://porofessor.gg/pregame/euw/One-EUW")
        self.assertEqual(payload["multiUrl"], "https://www.op.gg/multisearch/euw?summoners=One%23EUW")
        self.assertEqual(payload["poroUrl"], "https://porofessor.gg/pregame/euw/One-EUW")
        self.assertEqual(payload["uggUrl"], "https://u.gg/lol/multisearch?region=euw1&summoners=One-EUW")

        thread._tick()  # unchanged team is not re-sent right away
        self.assertEqual(broadcaster.broadcast_lobby_reveal.call_count, 1)

        state.phase = "InProgress"
        thread._tick()
        self.assertFalse(broadcaster.broadcast_lobby_reveal.call_args[0][0]["active"])
        thread._tick()  # cleared only once
        self.assertEqual(broadcaster.broadcast_lobby_reveal.call_count, 2)

    def test_does_nothing_outside_champ_select(self):
        thread, _, broadcaster = self._thread("Lobby")
        thread._tick()
        broadcaster.broadcast_lobby_reveal.assert_not_called()
        thread.chat.get_participants.assert_not_called()


if __name__ == "__main__":
    unittest.main()
