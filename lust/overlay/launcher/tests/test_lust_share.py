import unittest
from unittest.mock import patch

from launcher import lust_profile, lust_share

AHRI = {
    "id": 103, "name": "Ahri",
    "skins": [
        {"id": 103000, "isBase": True, "name": "Ahri"},
        {"id": 103027, "isBase": False, "name": "Spirit Blossom Ahri", "tilePath": "/lol-game-data/assets/ASSETS/x/tile27.jpg",
         "chromas": [{"id": 103028, "name": "Spirit Blossom Ahri (Ruby)", "colors": ["#D8263C", "#111111"]},
                     {"id": "bad"}]},
    ],
}
JINX = {"id": 222, "name": "Jinx", "skins": [{"id": 222004, "isBase": False, "name": "Firecracker Jinx"}]}
SKINS = {103: lust_profile.clean_skins(AHRI), 222: lust_profile.clean_skins(JINX)}


class CodeTests(unittest.TestCase):
    def test_round_trip_with_name(self):
        code = lust_share.encode({103: 103027, 222: 222004, 950: 950012}, "Bugra")
        self.assertTrue(code.startswith("LUST-"))
        self.assertEqual(lust_share.decode(code), {"name": "Bugra", "skins": {103: 103027, 222: 222004, 950: 950012}})

    def test_short(self):
        code = lust_share.encode({c: c * 1000 + 5 for c in range(1, 31)}, "Bugra")
        self.assertLess(len(code), 100)

    def test_list_of_ids_and_bad_entries(self):
        code = lust_share.encode([103027, 222000, "x", -5, 0])
        self.assertEqual(lust_share.decode(code)["skins"], {103: 103027})
        # a skin of another champion is not that champion's
        self.assertEqual(lust_share.decode(lust_share.encode({103: 222004}))["skins"], {})

    def test_long_names_are_cut_on_a_whole_letter(self):
        name = lust_share.decode(lust_share.encode({103: 103027}, "ŞŞŞŞŞŞŞŞŞŞ"))["name"]
        self.assertEqual(name, "ŞŞŞŞŞŞŞŞ")

    def test_pasted_with_spaces_and_text_around(self):
        code = lust_share.encode({103: 103027}, "Mert")
        self.assertEqual(lust_share.decode(f"al bunu:  {code[:10]}\n{code[10:]} "), lust_share.decode(code))

    def test_broken_codes(self):
        code = lust_share.encode({103: 103027})
        for bad in ("", "hello", "LUST-", "LUST-!!!", code[:-2], code[:-1] + ("A" if code[-1] != "A" else "B"), None, 5):
            self.assertIsNone(lust_share.decode(bad), bad)


class HubTests(unittest.TestCase):
    def setUp(self):
        self.history = {"103": 103027, "222": "path:skins/222000/x.fantome", "99": 99000}
        for target, value in (
            (lust_profile, {"skins": lambda c: SKINS.get(int(c), [])}),
            (lust_share, {"_champion_names": lambda: {103: "Ahri", 222: "Jinx"}, "_my_name": lambda: "Bugra"}),
        ):
            for name, fake in value.items():
                p = patch.object(target, name, side_effect=fake)
                p.start()
                self.addCleanup(p.stop)
        hist = patch("utils.core.historic.load_historic_map", side_effect=lambda: dict(self.history))
        hist.start()
        self.addCleanup(hist.stop)

        def write(champion, value):
            self.history[str(champion)] = value
        w = patch("utils.core.historic.write_historic_entry", side_effect=write)
        w.start()
        self.addCleanup(w.stop)

    def test_listing_leaves_out_custom_and_default_skins(self):
        data = lust_share.listing()
        self.assertEqual(data["custom"], 1)
        self.assertEqual([s["skinId"] for s in data["skins"]], [103027])
        self.assertEqual(data["skins"][0]["skin"], "Spirit Blossom Ahri")
        self.assertTrue(data["skins"][0]["tile"].endswith("tile27.jpg"))
        self.assertEqual(lust_share.decode(data["code"]), {"name": "Bugra", "skins": {103: 103027}})

    def test_chroma_is_named_with_its_skin(self):
        item = lust_share.describe({103: 103028})[0]
        self.assertEqual((item["skin"], item["chroma"], item["color"]), ("Spirit Blossom Ahri", "Spirit Blossom Ahri (Ruby)", "#D8263C"))

    def test_peek_marks_same_and_replaced(self):
        data = lust_share.peek(lust_share.encode({103: 103028, 222: 222004}, "Mert"))
        self.assertTrue(data["ok"])
        self.assertEqual(data["name"], "Mert")
        by = {s["champion"]: s for s in data["skins"]}
        self.assertTrue(by[103]["replaces"])
        self.assertFalse(by[222]["replaces"])  # a custom skin there is not a skin the code would replace
        self.assertFalse(lust_share.peek("nope")["ok"])

    def test_import_only_the_picked_champions(self):
        code = lust_share.encode({103: 103028, 222: 222004}, "Mert")
        message = lust_share.import_code(code, [222])
        self.assertIn("1 skin", message)
        self.assertEqual(self.history["222"], 222004)
        self.assertEqual(self.history["103"], 103027)
        lust_share.import_code(code)
        self.assertEqual(self.history["103"], 103028)
        self.assertIn("okunamadı", lust_share.import_code("LUST-xx"))
        self.assertIn("seçilmedi", lust_share.import_code(code, []))


if __name__ == "__main__":
    unittest.main()
