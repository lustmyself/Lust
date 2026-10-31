import unittest

from launcher import lust_patch

INDEX = """
<a href="/tr-tr/news/dev/some-dev-post/">Dev</a>
<a href="/tr-tr/news/game-updates/patch-26-21-notes/">Yama 26.21</a>
<a href="/tr-tr/news/game-updates/patch-26-20-notes/">Yama 26.20</a>
"""

ARTICLE = """
<h1 class="title">Yama 26.21 Notları</h1>
<h2 id="patch-champions">Şampiyonlar</h2>
<h3 class="change-title" id="patch-lux">Lux</h3>
<blockquote class="summary">Q ve E <b>hasarı</b> arttı.</blockquote>
<h3 class="change-title" id="patch-miss-fortune">Miss Fortune</h3>
<blockquote>Pasif &amp; R düzenlendi.</blockquote>
<h2 id="patch-items">Eşyalar</h2>
<h3 class="change-title">Kana Susamış</h3>
<h3 class="change-title">Ölümcül Hatırlatma</h3>
<h2 id="patch-bugfixes">Hatalar</h2>
<h3 class="change-title">Not a champion</h3>
"""


class PatchNotesTests(unittest.TestCase):
    def test_latest_link_is_the_first_patch_article(self):
        self.assertEqual(lust_patch.latest_link(INDEX),
                         "https://www.leagueoflegends.com/tr-tr/news/game-updates/patch-26-21-notes/")

    def test_latest_link_without_articles(self):
        self.assertIsNone(lust_patch.latest_link("<p>nothing</p>"))
        self.assertIsNone(lust_patch.latest_link(None))

    def test_version_from_the_link(self):
        self.assertEqual(lust_patch.version_of("/news/game-updates/patch-26-21-notes/"), "26.21")
        self.assertEqual(lust_patch.version_of("/news/game-updates/patch-25-S1-3-notes/"), "")

    def test_champions_and_items(self):
        data = lust_patch.parse_article(ARTICLE)
        self.assertEqual(data["title"], "Yama 26.21 Notları")
        self.assertEqual([c["name"] for c in data["champions"]], ["Lux", "Miss Fortune"])
        self.assertEqual(data["champions"][0]["summary"], "Q ve E hasarı arttı.")
        self.assertEqual(data["champions"][1]["alias"], "missfortune")
        self.assertEqual(data["champions"][1]["summary"], "Pasif & R düzenlendi.")
        self.assertEqual(data["items"], 2)

    def test_an_empty_article(self):
        self.assertEqual(lust_patch.parse_article(""), {"title": "", "champions": [], "items": 0})


if __name__ == "__main__":
    unittest.main()
