import io
import tempfile
import unittest
import zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from launcher import lust_maps

SHA = "a" * 64


class CatalogTests(unittest.TestCase):
    def test_only_https_files_with_a_hash_are_kept(self):
        items = lust_maps.clean_catalog({"maps": [
            {"id": "winter-rift", "name": "Winter Rift", "url": "https://example.com/w.fantome", "sha256": SHA,
             "preview": "http://example.com/p.png"},
            {"id": "no-hash", "url": "https://example.com/x.zip"},
            {"id": "plain", "url": "http://example.com/x.zip", "sha256": SHA},
            {"id": "../evil", "url": "https://example.com/x.zip", "sha256": SHA},
            {"id": "winter-rift", "url": "https://example.com/again.zip", "sha256": SHA},
        ]})
        self.assertEqual([i["id"] for i in items], ["winter-rift"])
        self.assertEqual(items[0]["file"], "map.fantome")
        self.assertEqual(items[0]["preview"], "")
        self.assertEqual(lust_maps.clean_catalog([1]), [])


class StorageTests(unittest.TestCase):
    def setUp(self):
        from injection.mods.storage import ModStorageService
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.storage = ModStorageService(self.root / "mods")
        p = patch.object(lust_maps, "_storage", return_value=self.storage)
        p.start()
        self.addCleanup(p.stop)
        self.saved = {}
        p = patch("utils.core.mod_historic.get_historic_mod", side_effect=lambda kind: self.saved.get(kind))
        p.start()
        self.addCleanup(p.stop)
        p = patch("utils.core.mod_historic.write_historic_mod", side_effect=self.saved.__setitem__)
        p.start()
        self.addCleanup(p.stop)
        p = patch("utils.core.mod_historic.clear_historic_mod", side_effect=lambda kind: self.saved.pop(kind, None))
        p.start()
        self.addCleanup(p.stop)
        self.state = SimpleNamespace(selected_map_mod={"mod_name": "old"})
        lust_maps.attach_state(self.state)
        self.addCleanup(lust_maps.attach_state, None)

    def _zip_bytes(self, with_preview=True) -> bytes:
        data = io.BytesIO()
        with zipfile.ZipFile(data, "w") as z:
            z.writestr("WAD/Map11.wad.client", b"map")
            if with_preview:
                z.writestr("preview.png", b"\x89PNG fake")
        return data.getvalue()

    def _upload(self, name="Winter Rift.zip", data=None):
        data = self._zip_bytes() if data is None else data
        return lust_maps.import_upload(name, io.BytesIO(data), len(data))

    def test_a_dropped_map_is_added_with_its_preview(self):
        self.assertIn("eklendi", self._upload())
        maps = lust_maps.installed()
        self.assertEqual([m["name"] for m in maps], ["Winter Rift"])
        self.assertTrue(maps[0]["preview"])
        self.assertEqual(lust_maps.preview_bytes(maps[0]["id"]), (b"\x89PNG fake", "image/png"))

    def _font_zip(self) -> bytes:
        data = io.BytesIO()
        with zipfile.ZipFile(data, "w") as z:
            z.writestr("META/info.json", b"{}")
            z.writestr("WAD/Bootstrap.windows.wad.client", b"font")
        return data.getvalue()

    def _patch_fonts(self):
        from launcher import lust_fonts
        p = patch.object(lust_fonts, "_storage", return_value=self.storage)
        p.start()
        self.addCleanup(p.stop)
        return lust_fonts

    def test_a_font_dropped_on_maps_goes_to_fonts(self):
        fonts = self._patch_fonts()
        self.assertIn("Fontlar", self._upload(name="koreanfont.fantome", data=self._font_zip()))
        self.assertEqual(lust_maps.installed(), [])
        self.assertEqual([e["name"] for e in self.storage.list_mods_for_category(fonts.CATEGORY)], ["koreanfont"])

    def test_a_font_already_among_the_maps_moves_to_fonts(self):
        fonts = self._patch_fonts()
        work = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__("shutil").rmtree(work, ignore_errors=True))
        (work / "koreanfont.zip").write_bytes(self._font_zip())
        lust_maps.import_file(work / "koreanfont.zip")
        self._upload()
        self.saved["map"] = "maps/koreanfont"
        self.assertEqual([m["name"] for m in lust_maps.installed()], ["Winter Rift"])
        self.assertNotIn("map", self.saved)
        fonts_dir = self.storage.list_mods_for_category(fonts.CATEGORY)
        self.assertEqual([e["name"] for e in fonts_dir], ["koreanfont"])
        self.assertTrue((self.storage.mods_root / fonts_dir[0]["path"] / "WAD" / "Bootstrap.windows.wad.client").is_file())

    def test_other_files_are_refused(self):
        self.assertIn("Yalnızca", self._upload(name="notes.txt"))
        self.assertEqual(lust_maps.installed(), [])

    def test_picking_a_map_saves_it_for_the_next_game(self):
        self._upload()
        map_id = lust_maps.installed()[0]["id"]
        lust_maps.select(map_id)
        self.assertEqual(self.saved["map"], map_id)
        self.assertIsNone(self.state.selected_map_mod)
        self.assertTrue(lust_maps.installed()[0]["selected"])
        lust_maps.select(None)
        self.assertNotIn("map", self.saved)

    def test_a_deleted_map_is_no_longer_picked(self):
        self._upload()
        map_id = lust_maps.installed()[0]["id"]
        lust_maps.select(map_id)
        lust_maps.delete(map_id)
        self.assertEqual(lust_maps.installed(), [])
        self.assertNotIn("map", self.saved)

    def test_a_catalog_map_with_the_wrong_hash_is_not_installed(self):
        data = self._zip_bytes()
        item = {"id": "winter", "name": "Winter Rift", "url": "https://example.com/w.zip", "sha256": SHA,
                "file": "map.zip", "preview": "", "author": "", "description": ""}

        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def raise_for_status(self):
                pass

            def iter_content(self, size):
                yield data

        with patch.object(lust_maps, "catalog", return_value=[item]), patch("requests.get", return_value=Response()):
            self.assertIn("eşleşmiyor", lust_maps.install("winter"))
            self.assertEqual(lust_maps.installed(), [])
            import hashlib
            item["sha256"] = hashlib.sha256(data).hexdigest()
            self.assertIn("kuruldu", lust_maps.install("winter"))
        self.assertEqual([m["name"] for m in lust_maps.installed()], ["Winter Rift"])


if __name__ == "__main__":
    unittest.main()
