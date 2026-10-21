import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from utils.integration import pengu_loader


class RestartKeepsPenguTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.patch = mock.patch.object(pengu_loader, "get_user_data_dir", return_value=Path(self.folder.name))
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        self.folder.cleanup()

    def test_a_restart_leaves_pengu_on_once(self):
        pengu_loader.keep_on_for_restart()
        with mock.patch.object(pengu_loader, "deactivate") as deactivate, \
                mock.patch.object(pengu_loader, "_read_session") as read_session:
            self.assertTrue(pengu_loader.restore_after_lust())
        deactivate.assert_not_called()
        read_session.assert_not_called()  # the session stays for the next Lust to adopt
        self.assertFalse((Path(self.folder.name) / "pengu_keep_for_restart").exists())

    def test_quitting_still_switches_pengu_off(self):
        with mock.patch.object(pengu_loader, "_read_session", return_value=None), \
                mock.patch.object(pengu_loader, "_ACTIVE_FLAG") as flag:
            flag.exists.return_value = False
            self.assertTrue(pengu_loader.restore_after_lust())

    def test_an_old_mark_is_ignored(self):
        pengu_loader.keep_on_for_restart()
        mark = Path(self.folder.name) / "pengu_keep_for_restart"
        old = time.time() - pengu_loader.RESTART_KEEP_S - 10
        os.utime(mark, (old, old))
        self.assertFalse(pengu_loader._restarting())
        self.assertFalse(mark.exists())


if __name__ == "__main__":
    unittest.main()
