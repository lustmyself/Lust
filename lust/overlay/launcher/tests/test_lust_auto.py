import unittest
from unittest import mock

from launcher import lust_auto


def _session(kind, me=1, completed=None, bans=(), team=()):
    actions = [[{"id": 7, "actorCellId": me, "type": kind, "isInProgress": True, "completed": False, "championId": 0}]]
    for cell, champion in completed or []:
        actions.insert(0, [{"id": 100 + cell, "actorCellId": cell, "type": "pick", "completed": True,
                            "championId": champion}])
    return {"localPlayerCellId": me, "actions": actions, "bans": {"myTeamBans": list(bans), "theirTeamBans": []},
            "myTeam": [{"cellId": cell, "championPickIntent": intent, "championId": 0} for cell, intent in team]}


ON = {"accept": True, "ban": True, "pick": True, "bans": [238, 157], "picks": [103, 99]}


class CleanTests(unittest.TestCase):
    def test_bad_values_fall_back(self):
        self.assertEqual(lust_auto.clean(None), lust_auto.DEFAULTS)
        self.assertEqual(lust_auto.clean({"accept": "yes", "bans": "x"}), lust_auto.DEFAULTS)

    def test_lists_keep_unique_positive_ids_up_to_the_max(self):
        out = lust_auto.clean({"picks": [1, 1, -2, True, "3", 4, 5, 6, 7, 8]})
        self.assertEqual(out["picks"], [1, 4, 5, 6, 7])


class ChooseTests(unittest.TestCase):
    def test_pick_takes_the_first_free_champion(self):
        session = _session("pick", completed=[(6, 103)])
        self.assertEqual(lust_auto.choose(session, ON), (7, 99, "pick"))

    def test_ban_skips_what_a_teammate_wants(self):
        session = _session("ban", team=[(2, 238)])
        self.assertEqual(lust_auto.choose(session, ON), (7, 157, "ban"))

    def test_ban_skips_banned_champions(self):
        session = _session("ban", bans=[238])
        self.assertEqual(lust_auto.choose(session, ON), (7, 157, "ban"))

    def test_only_what_the_client_allows(self):
        session = _session("pick")
        self.assertEqual(lust_auto.choose(session, ON, pickable={99}), (7, 99, "pick"))
        # A list from the client that leaves out every choice is not trusted
        self.assertEqual(lust_auto.choose(session, ON, pickable={1}), (7, 103, "pick"))

    def test_switched_off_does_nothing(self):
        self.assertIsNone(lust_auto.choose(_session("pick"), dict(ON, pick=False)))

    def test_someone_elses_turn(self):
        self.assertIsNone(lust_auto.choose(_session("pick", me=1) | {"localPlayerCellId": 3}, ON))

    def test_no_session(self):
        self.assertIsNone(lust_auto.choose(None, ON))

    def test_without_the_in_progress_flag_the_open_group_is_current(self):
        session = _session("pick")
        for group in session["actions"]:
            for action in group:
                action.pop("isInProgress", None)
        self.assertEqual(lust_auto.choose(session, ON), (7, 103, "pick"))

    def test_an_empty_allowed_list_does_not_block(self):
        session = _session("ban")
        self.assertEqual(lust_auto.choose(session, ON, bannable=None), (7, 238, "ban"))


class LockInTests(unittest.TestCase):
    def setUp(self):
        lust_auto._done.clear()

    def _run(self, session, times):
        calls = []

        def lcu(method, path, body=None):
            calls.append((method, path, body))
            return session if path.endswith("/session") else {}
        with mock.patch.object(lust_auto, "_lcu", side_effect=lcu):
            for _ in range(times):
                lust_auto._champ_select(dict(ON))
        return [c for c in calls if c[0] != "GET"]

    def test_hover_then_lock_in(self):
        sent = self._run(_session("ban"), 1)
        self.assertEqual(sent, [("PATCH", "/lol-champ-select/v1/session/actions/7", {"championId": 238}),
                                ("POST", "/lol-champ-select/v1/session/actions/7/complete", None)])

    def test_an_action_left_open_is_tried_again_a_few_times(self):
        sent = self._run(_session("ban"), lust_auto.MAX_TRIES + 3)
        self.assertEqual(len([c for c in sent if c[0] == "POST"]), lust_auto.MAX_TRIES)


if __name__ == "__main__":
    unittest.main()
