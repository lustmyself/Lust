import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from state import SharedState
from threads.handlers.injection_trigger import InjectionTrigger

AHRI = 103
CUSTOM = {
    "skin_id": 103000, "storage_skin_id": 103000, "target_skin_ids": [103000], "champion_id": AHRI,
    "mod_name": "Arcade Ahri", "display_name": "Arcade Ahri", "mod_path": "C:/x/arcade.fantome",
    "mod_folder_name": "lust-custom-arcade", "relative_path": None,
}


class LustCustomSkinInjectionTests(unittest.TestCase):
    """A custom skin switched on in the Lust hub plays on its champion's default skin"""

    def setUp(self):
        self.state = SharedState()
        self.state.locked_champ_id = AHRI
        self.state.owned_skin_ids = {103000}
        scraper = SimpleNamespace(cache=SimpleNamespace(chroma_id_map={}))
        self.trigger = InjectionTrigger(MagicMock(), self.state, MagicMock(), scraper)
        self.trigger._force_owned_skin = MagicMock()
        self.trigger._inject_custom_mod = MagicMock()
        self.trigger._inject_unowned_skin = MagicMock()
        for target, kwargs in (
            ("utils.core.historic.get_historic_skin_for_champion", {"return_value": None}),
            ("utils.core.mod_historic.load_mod_historic", {"return_value": {}}),
            ("injection.mods.storage.ModStorageService", {}),
        ):
            patcher = patch(target, **kwargs)
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_switched_on_skin_is_injected_on_the_default_skin(self):
        self.state.last_hovered_skin_id = 103000
        with patch("pengu.communication.lust_custom_skins.custom_mod_for", return_value=dict(CUSTOM)) as pick:
            self.trigger.trigger_injection("skin_103000", ticker_id=1)
        pick.assert_called_once_with(AHRI, 103000)
        self.trigger._inject_custom_mod.assert_called_once()
        self.assertEqual(self.trigger._inject_custom_mod.call_args.args[0]["mod_folder_name"], "lust-custom-arcade")
        self.assertEqual(self.state.selected_custom_mod["mod_name"], "Arcade Ahri")

    def test_a_chroma_counts_as_its_skin(self):
        self.trigger.skin_scraper.cache.chroma_id_map = {103019: {"skinId": 103018}}
        self.state.owned_skin_ids = {103000, 103018}
        self.state.last_hovered_skin_id = 103018
        self.state.selected_chroma_id = 103019
        with patch("pengu.communication.lust_custom_skins.custom_mod_for", return_value=None) as pick:
            self.trigger.trigger_injection("chroma_103019", ticker_id=1)
        pick.assert_called_once_with(AHRI, 103018)

    def test_nothing_is_injected_without_a_switched_on_skin(self):
        self.state.last_hovered_skin_id = 103000
        with patch("pengu.communication.lust_custom_skins.custom_mod_for", return_value=None):
            self.trigger.trigger_injection("skin_103000", ticker_id=1)
        self.trigger._inject_custom_mod.assert_not_called()
        self.assertIsNone(self.state.selected_custom_mod)


if __name__ == "__main__":
    unittest.main()
