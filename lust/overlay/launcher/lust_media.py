"""Spotify's "now playing" for the desktop hub: the song, its cover, the controls, mute
and a sound level for the visualizer.

The song and the controls come from Windows' media controls (the same ones the volume
flyout shows), so nothing signs in to Spotify. Mute and the sound level come from
Spotify's own audio session: muting it leaves every other sound alone.

It only works while the hub's Spotify page asks (watch()): the song once a second,
the sound level ten times a second, and nothing at all once the page stops asking.
"""

from __future__ import annotations

import asyncio
import threading
import time
from pathlib import Path
from typing import Optional

from utils.core.logging import get_logger

log = get_logger()

APP_ID = "spotify"            # the media session's app id contains this
WATCH_FOR_S = 4.0             # keep reading this long after the page last asked
LEVEL_EVERY_S = 0.1
INFO_EVERY_S = 1.0

_lock = threading.Lock()
_state: dict = {"available": False}
_level = 0.0
_cover_version = 0
_wanted_until = 0.0
_thread: Optional[threading.Thread] = None
_pending: list = []            # control actions for the worker thread


def _cover_path() -> Path:
    from utils.core.paths import get_user_data_dir
    folder = get_user_data_dir() / "media"
    folder.mkdir(parents=True, exist_ok=True)
    return folder / "cover.jpg"


def cover_path() -> Path:
    return _cover_path()


def watch() -> None:
    """The page shows the player: keep reading for a few seconds."""
    global _wanted_until, _thread
    _wanted_until = time.time() + WATCH_FOR_S
    with _lock:
        if _thread is None or not _thread.is_alive():
            _thread = threading.Thread(target=_worker, daemon=True, name="LustMedia")
            _thread.start()


def state() -> dict:
    watch()
    with _lock:
        return dict(_state)


def level() -> float:
    watch()
    return _level


def control(action: str) -> bool:
    """play_pause, next, previous or mute; done on the worker thread."""
    if action not in ("play_pause", "next", "previous", "mute"):
        return False
    watch()
    with _lock:
        _pending.append(action)
    return True


# ---- worker ----

async def _session():
    from winrt.windows.media.control import GlobalSystemMediaTransportControlsSessionManager as Manager
    manager = await Manager.request_async()
    for session in manager.get_sessions():
        if APP_ID in (session.source_app_user_model_id or "").lower():
            return session
    return None


async def _read_cover(info) -> Optional[bytes]:
    from winrt.windows.storage.streams import Buffer, DataReader, InputStreamOptions
    if info.thumbnail is None:
        return None
    stream = await info.thumbnail.open_read_async()
    size = int(stream.size)
    if not size or size > 8 * 1024 * 1024:
        return None
    buffer = Buffer(size)
    await stream.read_async(buffer, size, InputStreamOptions.READ_AHEAD)
    data = bytearray(buffer.length)
    DataReader.from_buffer(buffer).read_bytes(data)
    return bytes(data)


async def _read_info(last_key: str) -> str:
    global _cover_version
    session = await _session()
    if session is None:
        with _lock:
            _state.clear()
            _state["available"] = False
        return ""
    info = await session.try_get_media_properties_async()
    timeline = session.get_timeline_properties()
    playback = session.get_playback_info()
    key = f"{info.title}|{info.artist}"
    if key != last_key:
        try:
            cover = await _read_cover(info)
            if cover:
                _cover_path().write_bytes(cover)
                _cover_version += 1
        except Exception as exc:  # noqa: BLE001 - a missing cover leaves the old one
            log.debug(f"[Media] Could not read the cover: {exc}")
    position = timeline.position.total_seconds() if timeline.position else 0.0
    duration = timeline.end_time.total_seconds() if timeline.end_time else 0.0
    updated = timeline.last_updated_time.timestamp() if timeline.last_updated_time else time.time()
    playing = int(playback.playback_status) == 4  # PLAYING
    if playing:
        position = min(duration or position, position + max(0.0, time.time() - updated))
    with _lock:
        _state.update(available=True, title=info.title or "", artist=info.artist or "", playing=playing,
                      position=round(position, 1), duration=round(duration, 1), at=time.time(),
                      cover=_cover_version, muted=_muted())
    return key


async def _run_control(action: str) -> None:
    if action == "mute":
        _toggle_mute()
        with _lock:
            _state["muted"] = _muted()
        return
    session = await _session()
    if session is None:
        return
    if action == "play_pause":
        await session.try_toggle_play_pause_async()
    elif action == "next":
        await session.try_skip_next_async()
    elif action == "previous":
        await session.try_skip_previous_async()


def _audio_sessions():
    from pycaw.pycaw import AudioUtilities
    for session in AudioUtilities.GetAllSessions():
        try:
            if session.Process and session.Process.name().lower() == "spotify.exe":
                yield session
        except Exception:  # noqa: BLE001 - a process that just closed
            continue


def _muted() -> bool:
    try:
        sessions = list(_audio_sessions())
        return bool(sessions) and all(s.SimpleAudioVolume.GetMute() for s in sessions)
    except Exception:  # noqa: BLE001
        return False


def _toggle_mute() -> None:
    sessions = list(_audio_sessions())
    if not sessions:
        return
    mute = not all(s.SimpleAudioVolume.GetMute() for s in sessions)
    for session in sessions:
        session.SimpleAudioVolume.SetMute(mute, None)


def _peak() -> float:
    from pycaw.pycaw import IAudioMeterInformation
    peak = 0.0
    for session in _audio_sessions():
        meter = session._ctl.QueryInterface(IAudioMeterInformation)
        peak = max(peak, float(meter.GetPeakValue()))
    return peak


def _worker() -> None:
    global _level
    # COM in this thread must be multithreaded: comtypes starts a single-threaded one when it
    # is imported, and Windows' media controls then never deliver their async answers here
    import sys
    if not hasattr(sys, "coinit_flags"):
        sys.coinit_flags = 0  # COINIT_MULTITHREADED, read by comtypes when it is imported
    try:
        import comtypes
        comtypes.CoInitializeEx(comtypes.COINIT_MULTITHREADED)
    except Exception:  # noqa: BLE001 - already set up for this thread
        pass
    loop = asyncio.new_event_loop()
    last_key, next_info = "", 0.0
    try:
        while time.time() < _wanted_until:
            with _lock:
                actions, _pending[:] = list(_pending), []
            for action in actions:
                try:
                    loop.run_until_complete(_run_control(action))
                    next_info = 0.0
                except Exception as exc:  # noqa: BLE001
                    log.debug(f"[Media] {action} failed: {exc}")
            if time.time() >= next_info:
                try:
                    last_key = loop.run_until_complete(_read_info(last_key))
                except Exception as exc:  # noqa: BLE001
                    log.debug(f"[Media] Could not read what plays: {exc}")
                next_info = time.time() + INFO_EVERY_S
            try:
                _level = _peak() if _state.get("playing") else 0.0
            except Exception:  # noqa: BLE001
                _level = 0.0
            time.sleep(LEVEL_EVERY_S)
    finally:
        _level = 0.0
        loop.close()
