import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from launcher import lust_skins
from pengu.communication import lust_custom_skins

CHAMPIONS = [
    {"id": -1, "name": "None", "alias": "None"},
    {"id": 103, "name": "Ahri", "alias": "Ahri"},
    {"id": 266, "name": "Aatrox", "alias": "Aatrox"},
    {"id": "x", "name": "Bad", "alias": "Bad"},
]


def _mod(wad: str) -> bytes:
    data = io.BytesIO()
    with zipfile.ZipFile(data, "w") as z:
        z.writestr(f"WAD/{wad}.wad.client", b"wad")
    return data.getvalue()


class SkinsTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.folder = Path(tmp.name)
        p = patch.object(lust_custom_skins, "folder", return_value=self.folder)
        p.start()
        self.addCleanup(p.stop)
        p = patch.object(lust_skins, "champions", return_value=lust_skins.clean_champions(CHAMPIONS))
        p.start()
        self.addCleanup(p.stop)

    def test_champion_list_keeps_real_champions_by_name(self):
        names = [c["name"] for c in lust_skins.clean_champions(CHAMPIONS)]
        self.assertEqual(names, ["Aatrox", "Ahri"])
        self.assertEqual(lust_skins.clean_champions({"x": 1}), [])

    def test_listing_guesses_the_champion_from_the_wad(self):
        (self.folder / "Star Ahri.zip").write_bytes(_mod("Ahri"))
        (self.folder / "Mystery.zip").write_bytes(_mod("Common"))
        data = lust_skins.listing()
        by_name = {s["name"]: s for s in data["skins"]}
        self.assertEqual(by_name["Star Ahri.zip"]["championId"], 103)
        self.assertEqual(by_name["Star Ahri.zip"]["champion"], "Ahri")
        self.assertIsNone(by_name["Mystery.zip"]["championId"])
        self.assertEqual([c["name"] for c in data["champions"]], ["Aatrox", "Ahri"])

    def test_toggle_needs_a_champion_and_keeps_one_per_champion(self):
        (self.folder / "a.zip").write_bytes(_mod("Common"))
        (self.folder / "b.zip").write_bytes(_mod("Common"))
        lust_skins.listing()
        self.assertEqual(lust_skins.toggle("a.zip", True), "Önce şampiyonu seç")
        lust_skins.set_champion("a.zip", 266)
        lust_skins.set_champion("b.zip", 266)
        self.assertTrue(lust_skins.toggle("a.zip", True))
        lust_skins.toggle("b.zip", True)
        on = {s["name"]: s["enabled"] for s in lust_skins.listing()["skins"]}
        self.assertEqual(on, {"a.zip": False, "b.zip": True})

    def test_upload_and_delete(self):
        body = _mod("Ahri")
        self.assertEqual(lust_skins.import_upload("bad.exe", io.BytesIO(body), len(body)),
                         "Yalnızca .zip, .fantome ve .modpkg dosyaları eklenebilir")
        self.assertEqual(lust_skins.import_upload("../x.zip", io.BytesIO(body), len(body)), "x eklendi")
        self.assertTrue((self.folder / "x.zip").is_file())
        self.assertEqual(lust_skins.import_upload("y.zip", io.BytesIO(body[:5]), len(body)), "Dosya yarım geldi")
        self.assertEqual(sorted(p.name for p in self.folder.iterdir()), ["x.zip"])
        lust_skins.listing()
        lust_skins.toggle("x.zip", True)
        self.assertEqual(lust_skins.delete("x.zip"), "x silindi")
        state = json.loads((self.folder / lust_custom_skins.STATE_FILE).read_text(encoding="utf-8"))
        self.assertNotIn("x.zip", state)
        self.assertEqual(lust_skins.delete("../secret.zip"), "")


if __name__ == "__main__":
    unittest.main()
