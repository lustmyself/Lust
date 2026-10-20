import base64
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pengu.communication import lust_assets


class LustAssetsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        patcher = patch.object(lust_assets, "get_user_data_dir", return_value=self.root)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self.tmp.cleanup)

    def _ask(self, **payload):
        return lust_assets.handle({"type": "lust-assets", "requestId": "r1", **payload})

    def test_chunked_upload_then_list_and_delete(self):
        data = b"x" * 1000 + b"y" * 1000
        chunks = [data[:1000], data[1000:]]
        for index, chunk in enumerate(chunks):
            reply = self._ask(kind="wallpaper", action="save", name="clip.webm", index=index, total=2,
                              data=base64.b64encode(chunk).decode())
            self.assertEqual(reply["error"], "")
        self.assertTrue(reply["done"])
        self.assertEqual(reply["requestId"], "r1")
        folder = self.root / "Pengu Loader" / "plugins" / "LUST-Theme" / "assets" / "backgrounds" / "wallpapers"
        self.assertEqual((folder / "clip.webm").read_bytes(), data)
        self.assertEqual(self._ask(kind="wallpaper", action="list")["files"], ["clip.webm"])

        reply = self._ask(kind="wallpaper", action="delete", name="clip.webm")
        self.assertEqual(reply["files"], [])

    def test_rejects_bad_names_and_kinds(self):
        for name in ["../evil.webm", "a\\b.webm", "notes.txt", ".hidden.webm", ""]:
            reply = self._ask(kind="wallpaper", action="save", name=name, index=0, total=1, data="")
            self.assertEqual(reply["error"], "bad file name", name)
        self.assertEqual(self._ask(kind="scripts", action="list")["error"], "unknown kind")

    def test_a_chunk_without_its_start_is_refused(self):
        reply = self._ask(kind="font", action="save", name="f.ttf", index=1, total=2,
                          data=base64.b64encode(b"z").decode())
        self.assertEqual(reply["error"], "upload interrupted")
        self.assertEqual(reply["files"], [])


if __name__ == "__main__":
    unittest.main()
