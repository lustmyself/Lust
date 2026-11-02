import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from launcher import lust_share


class FakeLcu:
    def __init__(self, lobby=None, session=None, flow=None):
        self.lobby, self.session, self.flow = lobby, session, flow
        self.ok = True
        self.current_summoner = {"summonerId": 1, "puuid": "me-puuid", "gameName": "Me"}

    def get(self, path, timeout=1.0):
        return {"/lol-lobby/v2/lobby": self.lobby, "/lol-gameflow/v1/session": self.flow}.get(path)


def team(cell=0, side=1, size=5):
    return [{"cellId": i, "team": side, "summonerId": 10 + i, "puuid": f"p{i}"} for i in range(size)]


class RoomsTest(unittest.TestCase):
    def test_lobby_room_needs_someone_else(self):
        alone = {"partyId": "abc", "members": [{"summonerId": 1}]}
        duo = {"partyId": "abc", "members": [{"summonerId": 1}, {"summonerId": 2}]}
        self.assertIsNone(lust_share.lobby_room(alone))
        self.assertIsNone(lust_share.lobby_room({"members": duo["members"]}))
        self.assertRegex(lust_share.lobby_room(duo), r"^[0-9a-f]{32}$")
        self.assertEqual(lust_share.lobby_room(duo), lust_share.lobby_room(dict(duo)))
        self.assertNotEqual(lust_share.lobby_room(duo), lust_share.lobby_room({**duo, "partyId": "xyz"}))

    def test_team_room_same_for_the_team_not_the_enemies(self):
        mine = {"gameId": 77, "localPlayerCellId": 2, "myTeam": team(side=1)}
        mate = {"gameId": 77, "localPlayerCellId": 4, "myTeam": team(side=1)}
        enemy = {"gameId": 77, "localPlayerCellId": 6, "myTeam": [
            {"cellId": 5 + i, "team": 2} for i in range(5)]}
        self.assertEqual(lust_share.team_room(mine), lust_share.team_room(mate))
        self.assertNotEqual(lust_share.team_room(mine), lust_share.team_room(enemy))
        self.assertNotEqual(lust_share.team_room(mine), lust_share.team_room({**mine, "gameId": 78}))

    def test_team_room_needs_a_game_and_a_team(self):
        self.assertIsNone(lust_share.team_room({"gameId": 0, "myTeam": team()}))
        self.assertIsNone(lust_share.team_room({"gameId": 5, "myTeam": team(size=1)}))
        self.assertIsNotNone(lust_share.team_room({"gameId": 0, "myTeam": team()}, game_id="5"))

    def test_rooms_for_each_phase(self):
        duo = {"partyId": "abc", "members": [{}, {}]}
        lcu = FakeLcu(lobby=duo, session={"gameId": 0, "localPlayerCellId": 0, "myTeam": team()},
                      flow={"gameData": {"gameId": 9}})
        self.assertEqual(lust_share.rooms_for(lcu, "Lobby"), {lust_share.lobby_room(duo)})
        self.assertEqual(lust_share.rooms_for(lcu, "ChampSelect"),
                         {lust_share.team_room(lcu.session, 9)})
        self.assertIsNone(lust_share.rooms_for(lcu, "InProgress"))
        self.assertEqual(lust_share.rooms_for(lcu, "EndOfGame"), set())


class ManagerTest(unittest.TestCase):
    def make(self, phase="Lobby"):
        state = SimpleNamespace(phase=phase, locked_champ_id=None, hovered_champ_id=None,
                                last_hovered_skin_id=None, selected_chroma_id=None, selected_custom_mod=None,
                                historic_mode_active=False, historic_skin_id=None, random_mode_active=False,
                                random_skin_id=None, party_manager=None)
        manager = lust_share._manager_class()(FakeLcu(), state)
        asyncio.run(self._enable(manager))
        return manager

    async def _enable(self, manager):
        await manager.enable()
        manager._running = False
        for task in (manager._lobby_check_task, manager._skin_broadcast_task):
            task.cancel()

    def test_enable_opens_no_room(self):
        manager = self.make()
        self.assertTrue(manager.enabled)
        self.assertEqual(manager._relays, {})
        self.assertEqual(manager.my_puuid, "me-puuid")

    def test_state_carries_the_icon(self):
        manager = self.make()
        with patch.object(lust_share, "_my_icon", return_value=4567):
            self.assertEqual(manager._current_skin_state(), {"icon_id": 4567, "puuid": "me-puuid"})
        with patch.object(lust_share, "_my_icon", return_value=0):
            self.assertIsNone(manager._current_skin_state())

    def test_last_pick_kept_after_champ_select(self):
        manager = self.make(phase="InProgress")
        manager._skin_state = {"champion_id": 103, "skin_id": 103001, "icon_id": 1, "puuid": "x"}
        with patch.object(lust_share, "_my_icon", return_value=0):
            self.assertEqual(manager._current_skin_state(), {"champion_id": 103, "skin_id": 103001})

    def test_shared_icons_and_no_room_following(self):
        manager = self.make()
        relay = SimpleNamespace(connected=True, members=[
            {"summoner_id": 1, "summoner_name": "Me", "skin": {"icon_id": 9}},
            {"summoner_id": 2, "summoner_name": "Duo", "skin": {"icon_id": 29, "puuid": "duo",
                                                               "rooms": ["a" * 32]}},
            {"summoner_id": 3, "summoner_name": "Plain", "skin": {"champion_id": 1, "skin_id": 1001}},
        ])
        manager._relays["k"] = relay
        self.assertEqual(manager.shared_icons(), [{"summonerId": "2", "iconId": 29, "puuid": "duo"}])
        manager._follow_advertised_rooms()
        self.assertEqual(list(manager._relays), ["k"])

    def test_sync_rooms_joins_and_leaves(self):
        manager = self.make()
        old = SimpleNamespace(disconnect=AsyncMock(), members=[], connected=True)
        manager._relays["old"] = old
        joined = []

        async def join(key):
            joined.append(key)
            manager._relays[key] = SimpleNamespace(members=[], connected=True, resume=lambda: None)

        manager._join_room = join
        asyncio.run(manager.sync_rooms({"new"}))
        old.disconnect.assert_awaited()
        self.assertEqual(joined, ["new"])
        self.assertEqual(list(manager._relays), ["new"])


class SwitchTest(unittest.TestCase):
    def test_off_without_a_relay_or_the_setting(self):
        with patch.object(lust_share, "relay_url", return_value=""):
            self.assertFalse(lust_share.wanted())
        with patch.object(lust_share, "relay_url", return_value="wss://x"), \
                patch("launcher.lust_settings.enabled", return_value=False):
            self.assertFalse(lust_share.wanted())
        with patch.object(lust_share, "relay_url", return_value="wss://x"), \
                patch("launcher.lust_settings.enabled", return_value=True):
            self.assertTrue(lust_share.wanted())

    def test_no_icons_before_start(self):
        with patch.object(lust_share, "_runner", None):
            self.assertEqual(lust_share.shared_icons(), [])
            self.assertEqual(lust_share.status()["running"], False)


if __name__ == "__main__":
    unittest.main()
