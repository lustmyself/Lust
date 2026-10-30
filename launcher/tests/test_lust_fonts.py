import io
import tempfile
import unittest
import zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from launcher import lust_fonts

BUNDLED = Path(__file__).resolve().parents[2] / "assets" / "lust_fonts" / lust_fonts.DEFAULT_FILE


class FontTests(unittest.TestCase):
    def setUp(self):
        from injection.mods.storage import ModStorageService
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.storage = ModStorageService(self.root / "mods")
        self.saved = {}
        for target, kwargs in (
            ("launcher.lust_fonts._storage", {"return_value": self.storage}),
            ("launcher.lust_fonts._marker_path", {"return_value": self.root / "lust_fonts.json"}),
            ("launcher.lust_fonts._bundled", {"return_value": BUNDLED}),
            ("utils.core.mod_historic.get_historic_mod", {"side_effect": lambda kind: self.saved.get(kind)}),
            ("utils.core.mod_historic.write_historic_mod", {"side_effect": self.saved.__setitem__}),
            ("utils.core.mod_historic.clear_historic_mod", {"side_effect": lambda kind: self.saved.pop(kind, None)}),
        ):
            p = patch(target, **kwargs)
            p.start()
            self.addCleanup(p.stop)
        self.state = SimpleNamespace(selected_font_mod={"mod_name": "old"})
        lust_fonts.attach_state(self.state)
        self.addCleanup(lust_fonts.attach_state, None)

    def _upload(self, name="Comic.fantome"):
        data = io.BytesIO()
        with zipfile.ZipFile(data, "w") as z:
            z.writestr("WAD/Bootstrap.windows.wad.client", b"font")
        data = data.getvalue()
        return lust_fonts.import_upload(name, io.BytesIO(data), len(data))

    def test_the_bundled_font_is_a_fantome(self):
        with zipfile.ZipFile(BUNDLED) as z:
            self.assertIn("WAD/Bootstrap.windows.wad.client", z.namelist())

    def test_korean_is_added_and_picked_on_a_fresh_install(self):
        listing = lust_fonts.listing()
        self.assertEqual([f["name"] for f in listing["installed"]], [lust_fonts.DEFAULT_NAME])
        self.assertTrue(listing["installed"][0]["lust"])
        self.assertTrue(listing["installed"][0]["selected"])
        self.assertEqual(self.saved["font"], listing["selected"])

    def test_the_default_does_not_come_back_once_the_user_chose(self):
        lust_fonts.ensure_default()
        lust_fonts.select(None)
        self.assertIsNone(self.state.selected_font_mod)
        self.assertIsNone(lust_fonts.listing()["selected"])
        lust_fonts.delete(lust_fonts.installed()[0]["id"])
        self.assertEqual(lust_fonts.listing()["installed"], [])

    def test_an_existing_pick_is_kept(self):
        self._upload()
        mine = lust_fonts.installed()[0]["id"]
        lust_fonts.select(mine)
        lust_fonts.ensure_default()
        self.assertEqual(self.saved["font"], mine)
        self.assertEqual(len(lust_fonts.installed()), 2)

    def test_a_dropped_font_can_be_picked(self):
        lust_fonts.ensure_default()
        self.assertIn("eklendi", self._upload())
        self.assertIn("Yalnızca", self._upload(name="font.ttf"))
        comic = next(f for f in lust_fonts.installed() if not f["lust"])
        self.assertIn("Comic", lust_fonts.select(comic["id"]))
        self.assertEqual(self.saved["font"], comic["id"])


if __name__ == "__main__":
    unittest.main()
