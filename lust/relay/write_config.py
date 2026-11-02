"""Write party/network/relay_config.py for a build: the address of Lust's relay.

LUST_RELAY_URL wins when set. Otherwise the address comes from the Cloudflare account
the relay is deployed to (CLOUDFLARE_API_TOKEN, CLOUDFLARE_ACCOUNT_ID): the worker
lust-party-relay answers on <account's workers.dev subdomain>. Without either, the
address is empty and Lust shares no skins.
"""

import json
import os
import sys
import urllib.request
from pathlib import Path

WORKER = "lust-party-relay"
OUT = Path(__file__).resolve().parents[2] / "party" / "network" / "relay_config.py"


def workers_subdomain(token: str, account: str) -> str:
    request = urllib.request.Request(
        f"https://api.cloudflare.com/client/v4/accounts/{account}/workers/subdomain",
        headers={"Authorization": f"Bearer {token}"},
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.load(response)["result"]["subdomain"]


def relay_url() -> str:
    url = os.environ.get("LUST_RELAY_URL", "").strip()
    if url:
        return url
    token = os.environ.get("CLOUDFLARE_API_TOKEN", "").strip()
    account = os.environ.get("CLOUDFLARE_ACCOUNT_ID", "").strip()
    if not token or not account:
        return ""
    try:
        return f"wss://{WORKER}.{workers_subdomain(token, account)}.workers.dev"
    except Exception as e:  # noqa: BLE001
        print(f"Could not read the workers.dev subdomain: {e}", file=sys.stderr)
        return ""


if __name__ == "__main__":
    url = relay_url()
    OUT.write_text(f"RELAY_URL = {url!r}\n", encoding="utf-8")
    print(f"Relay: {url or '(none, skin sharing is off)'}")
