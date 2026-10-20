"""Start with Windows is on by default.

The first time Lust runs it registers itself to start at logon, once. A player who
unticks "Start with Windows" afterwards keeps it off: the [General]
autostartDefaultApplied flag stops this from turning it back on.
"""

from __future__ import annotations

import sys

from config import get_config_option, set_config_option
from utils.core.logging import get_logger
from utils.system.admin_utils import register_autostart

log = get_logger()

FLAG = "autostartDefaultApplied"


def apply_autostart_default() -> None:
    if sys.platform != "win32" or not getattr(sys, "frozen", False):
        return
    if get_config_option("General", FLAG) == "1":
        return
    ok, message = register_autostart()
    log.info(f"[Autostart] Default on first run: {message}")
    if ok:
        set_config_option("General", FLAG, "1")
