"""After a deploy: two players join one room and see each other's pick, and two League
friends find each other in the friends directory (run from the repo root)."""

import asyncio
import json
import sys
import urllib.request

import websockets

sys.path.insert(0, ".")
exec(open("party/network/relay_config.py").read())  # RELAY_URL

KEY = "deploycheck" + "0" * 21
URL = f"{RELAY_URL}/room?key={KEY}&v=1.4.9.82"  # noqa: F821


async def join(summoner_id, skin=None):
    ws = await websockets.connect(URL, open_timeout=20)
    await ws.send(json.dumps({"type": "join", "summoner_id": summoner_id, "summoner_name": f"check{summoner_id}"}))
    if skin:
        await ws.send(json.dumps({"type": "skin", "skin": skin}))
    return ws


async def main():
    a = await join(1, {"champion_id": 103, "skin_id": 103001, "icon_id": 29})
    b = await join(2)
    seen = None
    for _ in range(10):
        msg = json.loads(await asyncio.wait_for(b.recv(), 10))
        members = {m["summoner_id"]: m for m in msg.get("members", [])}
        if 1 in members and members[1].get("skin"):
            seen = members[1]["skin"]
            break
    await a.close()
    await b.close()
    if seen != {"champion_id": 103, "skin_id": 103001, "icon_id": 29}:
        raise SystemExit(f"Player 2 did not see player 1's pick: {seen}")
    print("Rooms work: player 2 saw", seen)


def directory(me, friends):
    base = RELAY_URL.replace("wss://", "https://", 1)  # noqa: F821
    request = urllib.request.Request(f"{base}/friends?v=1.4.9.92", data=json.dumps({"me": me, "friends": friends}).encode(),
                                     method="POST", headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.loads(response.read())["matches"]


def check_directory():
    a, b, c = (("dc0000000" + x).ljust(32, "0") for x in "abc")
    directory(a, [b, c])
    if directory(b, [a]) != [a]:
        raise SystemExit("Friends directory: b did not find a")
    if directory(c, []) != []:
        raise SystemExit("Friends directory: c found someone who is not on its list")
    print("Friends directory works")


asyncio.run(main())
check_directory()
