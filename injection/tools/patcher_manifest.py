#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Where Lust gets the LTK patcher, kept outside the code.

lust/patcher.json in Lust's repo lists the ltk_patcher.zip download pages, the builds
known to work with Lust (SHA-256 of both files, with their end-of-life date) and DLL
builds known to refuse Lust. Lust reads it from GitHub at most every few hours and keeps
the last copy, so a new link or a new build needs no Lust release. Without a network or a
copy it falls back to DEFAULT_MANIFEST.

A build listed under "builds" is taken even without League Toolkit's signature: the LTK
Patcher License asks anyone who redistributes the files to remove that signature.
"""

import hashlib
import json
import threading
import time
from pathlib import Path
from typing import Optional

from utils.core.logging import get_logger

log = get_logger()

MANIFEST_URL = "https://raw.githubusercontent.com/lustmyself/Lust/main/lust/patcher.json"
CACHE_FILE = "patcher-manifest.json"
REFRESH_S = 6 * 60 * 60
FETCH_TIMEOUT_S = 6

DEFAULT_MANIFEST = {
    # ltk_patcher.zip, as Rose's Discord shares it (#tutorial, "NEW LTK FILES REQUIRED", 2026-10-22)
    "downloads": [
        {"url": "https://www.mediafire.com/file/g0lzcgpr97jd9r3/ltk_patcher.zip/file",
         "source": "Rose Discord #tutorial"},
    ],
    "builds": [],
    "locked": [],
}

_lock = threading.Lock()
_memo: dict = {"at": 0.0, "manifest": None}


def _is_sha256(value) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value.lower())


def clean(data) -> Optional[dict]:
    """The manifest's usable parts, or None when it is not a manifest at all.
    Only https download pages and well-formed hashes are kept."""
    if not isinstance(data, dict):
        return None
    downloads = [
        {"url": d["url"], "source": str(d.get("source") or "")}
        for d in data.get("downloads") or [] if isinstance(d, dict)
        and isinstance(d.get("url"), str) and d["url"].startswith("https://") and len(d["url"]) < 500
    ]
    builds = []
    for b in data.get("builds") or []:
        if isinstance(b, dict) and _is_sha256(b.get("dll")) and _is_sha256(b.get("host")):
            eol = b.get("eol")
            builds.append({"dll": b["dll"].lower(), "host": b["host"].lower(),
                           "eol": eol if isinstance(eol, int) and eol > 0 else None,
                           "note": str(b.get("note") or "")})
    locked = [h.lower() for h in data.get("locked") or [] if _is_sha256(h)]
    if not downloads:
        downloads = list(DEFAULT_MANIFEST["downloads"])
    return {"downloads": downloads, "builds": builds, "locked": locked}


def _cache_path() -> Optional[Path]:
    try:
        from utils.core.paths import get_user_data_dir
        return get_user_data_dir() / CACHE_FILE
    except Exception:  # noqa: BLE001
        return None


def _read_cache() -> Optional[dict]:
    path = _cache_path()
    try:
        return clean(json.loads(path.read_text(encoding="utf-8"))) if path else None
    except (OSError, ValueError):
        return None


def _fetch() -> Optional[dict]:
    try:
        import requests
        from config import APP_USER_AGENT
        response = requests.get(MANIFEST_URL, timeout=FETCH_TIMEOUT_S, headers={"User-Agent": APP_USER_AGENT})
        response.raise_for_status()
        manifest = clean(response.json())
    except Exception as e:  # noqa: BLE001 - offline, GitHub down, a bad edit: keep the last copy
        log.info(f"[LTK] Could not read the patcher manifest: {e}")
        return None
    if manifest is None:
        return None
    path = _cache_path()
    if path:
        try:
            from utils.core.atomic_file import write_text_atomic
            write_text_atomic(path, json.dumps(manifest, indent=1))
        except Exception as e:  # noqa: BLE001
            log.debug(f"[LTK] Could not keep the patcher manifest: {e}")
    return manifest


def manifest(refresh: bool = False) -> dict:
    """The patcher manifest, read from GitHub when the copy at hand is a few hours old."""
    with _lock:
        now = time.monotonic()
        if not refresh and _memo["at"] and now - _memo["at"] < REFRESH_S:
            return _memo["manifest"]
        result = _fetch() or _memo["manifest"] or _read_cache() or clean(DEFAULT_MANIFEST)
        _memo.update(at=now, manifest=result)
        return result


def current() -> dict:
    """The manifest at hand, without the network: the one read last, the kept copy, or the default."""
    with _lock:
        if _memo["manifest"] is None:
            _memo["manifest"] = _read_cache() or clean(DEFAULT_MANIFEST)
        return _memo["manifest"]


def download_url() -> str:
    """The ltk_patcher.zip page Lust sends players to."""
    try:
        return current()["downloads"][0]["url"]
    except Exception:  # noqa: BLE001
        return DEFAULT_MANIFEST["downloads"][0]["url"]


def sha256_of(path: Path) -> Optional[str]:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def known_build(dll: Path, host: Path) -> Optional[dict]:
    """The manifest entry for this pair of patcher files, or None when it lists neither."""
    dll_sha, host_sha = sha256_of(dll), sha256_of(host)
    if not dll_sha or not host_sha:
        return None
    try:
        builds = current()["builds"]
    except Exception:  # noqa: BLE001
        return None
    return next((b for b in builds if b["dll"] == dll_sha and b["host"] == host_sha), None)


def locked_digests() -> set:
    """DLL builds the manifest knows refuse Lust."""
    try:
        return set(current()["locked"])
    except Exception:  # noqa: BLE001
        return set()


def newest_eol() -> Optional[int]:
    """The latest end-of-life date among the builds the manifest lists."""
    try:
        dates = [b["eol"] for b in current()["builds"] if b["eol"]]
    except Exception:  # noqa: BLE001
        return None
    return max(dates) if dates else None
