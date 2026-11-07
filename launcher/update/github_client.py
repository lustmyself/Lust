"""
GitHub Client
Handles GitHub API interactions for release checking
"""

from __future__ import annotations

import re
from typing import Optional

import requests

from utils.core.logging import get_logger

log = get_logger()

# Lust's own releases. Never point this at Rose's: its update would replace Lust with Rose.
# An empty value turns update checks off.
GITHUB_RELEASE_API = "https://api.github.com/repos/lustmyself/Lust/releases/latest"


class GitHubClient:
    """Client for interacting with GitHub API"""
    
    def __init__(self, timeout: int = 20):
        self.timeout = timeout
    
    def get_latest_release(self) -> Optional[dict]:
        """Get the latest release information from GitHub
        
        Returns:
            Release data dictionary or None if failed
        """
        if not GITHUB_RELEASE_API:
            log.info("Update check skipped: no release repository configured")
            return None
        try:
            response = requests.get(GITHUB_RELEASE_API, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            log.warning("Update check failed while fetching latest release: %s", e)
            return self._latest_from_web()

    def _latest_from_web(self) -> Optional[dict]:
        """The latest release from github.com itself, which the API limit does not cover."""
        repo = GITHUB_RELEASE_API.split("/repos/", 1)[-1].rsplit("/releases", 1)[0]
        try:
            response = requests.get(f"https://github.com/{repo}/releases/latest",
                                    timeout=self.timeout, allow_redirects=False)
            tag = response.headers.get("Location", "").rstrip("/").rsplit("/tag/", 1)[-1]
        except Exception as e:
            log.warning("Update check from github.com failed too: %s", e)
            return None
        if response.status_code not in (301, 302) or not re.fullmatch(r"v?[0-9][0-9A-Za-z.]*", tag):
            log.warning("Update check from github.com found no release tag")
            return None
        version = tag.lstrip("vV")
        name = f"update_package_{version}.zip"
        log.info("Latest release %s found on github.com (API limit reached)", tag)
        return {"tag_name": tag, "assets": [{
            "name": name, "size": 0,
            "browser_download_url": f"https://github.com/{repo}/releases/download/{tag}/{name}",
        }]}
    
    def get_release_version(self, release: dict) -> str:
        """Extract version string from release data"""
        return release.get("tag_name") or release.get("name") or ""
    
    def get_zip_asset(self, release: dict) -> Optional[dict]:
        """Get the ZIP asset from release data"""
        assets = release.get("assets", [])
        return next((a for a in assets if a.get("name", "").lower().endswith(".zip")), None)
    
    def get_hash_asset(self, release: dict) -> Optional[dict]:
        """Get the hash file asset from release data"""
        assets = release.get("assets", [])
        return next((a for a in assets if a.get("name", "").lower() == "hashes.game.txt"), None)

