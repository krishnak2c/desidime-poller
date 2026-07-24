#!/usr/bin/env python3
"""Gold & Silver Monitor — Haldwani 22K gold + silver. Polls bankbazaar, notifies on change."""

import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timezone

STATE_FILE = "rates-state.json"
GOLD_URL = "https://www.bankbazaar.com/gold-rate-haldwani.html"
SILVER_URL = "https://www.bankbazaar.com/silver-rate-haldwani.html"


def fetch(url):
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.read().decode("utf-8", errors="replace")


def extract_gold(html):
    """Parse 22K/1g from gold rate page. Table: Gram | Today | Yesterday | Change"""
    m = re.search(
        r"<td[^>]*>\s*1\s*gram\s*</td>\s*"
        r"<td[^>]*>\s*<[^>]*>\s*[Rs\u20B9]+\s*([\d,]+)\s*<",
        html, re.DOTALL | re.IGNORECASE
    )
    return m.group(1).replace(",", "") if m else None


def extract_silver(html):
    """Parse silver 1g from silver rate page. Same table structure."""
    m = re.search(
        r"<td[^>]*>\s*1\s*gram\s*</td>\s*"
        r"<td[^>]*>\s*<[^>]*>\s*[Rs\u20B9]+\s*([\d,]+)\s*<",
        html, re.DOTALL | re.IGNORECASE
    )
    return m.group(1).replace(",", "") if m else None


def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {"date": "", "gold": "0", "silver": "0", "first_run": True}


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)


def send_ntfy(gold, silver, prev_gold, prev_silver, gd, sd):
    topic = os.environ.get("NTFY_TOPIC", "")
    if not topic:
        return

    g_dir = "UP" if gd > 0 else "DOWN" if gd < 0 else ""
    s_dir = "UP" if sd > 0 else "DOWN" if sd < 0 else ""
    gc = (" " + g_dir + " Rs." + format(abs(gd), ",")) if gd != 0 else " (same)"
    sc = (" " + s_dir + " Rs." + format(abs(sd), ",")) if sd != 0 else " (same)"

    title = "Gold: Rs." + gold + "/g  |  Silver: Rs." + silver + "/g"
    body = "\n".join([
        "Haldwani — 22K Gold",
        "Today: Rs." + gold + "/g  (prev: Rs." + prev_gold + "/g" + gc + ")",
        "",
        "Silver",
        "Today: Rs." + silver + "/g  (prev: Rs." + prev_silver + "/g" + sc + ")",
        "",
        GOLD_URL,
    ])

    headers = {"Title": title[:80], "Priority": "3", "Tags": "droplet"}
    req = urllib.request.Request(
        "https://ntfy.sh/" + topic, data=body.encode(), headers=headers
    )
    try:
        urllib.request.urlopen(req, timeout=5)
        print("  ntfy sent")
    except Exception as e:
        print("  ntfy failed: " + str(e))


def main():
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    print("[" + ts + "] Rates Monitor starting")

    state = load_state()
    print("[" + ts + "] State: first_run=" + str(state.get("first_run"))
          + " gold=" + str(state.get("gold")) + " silver=" + str(state.get("silver")))

    try:
        gold_html = fetch(GOLD_URL)
        silver_html = fetch(SILVER_URL)
    except Exception as e:
        print("[" + ts + "] Fetch failed: " + str(e))
        sys.exit(1)

    gold = extract_gold(gold_html)
    silver = extract_silver(silver_html)

    if not gold or not silver:
        print("[" + ts + "] Parse failed — gold=" + str(gold) + " silver=" + str(silver))
        sys.exit(0)

    print("[" + ts + "] Gold22K: Rs." + gold + "/g  |  Silver: Rs." + silver + "/g")

    if state.get("first_run"):
        state["first_run"] = False
        state["date"] = ts[:10]
        state["gold"] = gold
        state["silver"] = silver
        save_state(state)
        print("[" + ts + "] Initialized — gold: Rs." + gold + ", silver: Rs." + silver)
        return

    pg = int(state.get("gold", "0"))
    ps = int(state.get("silver", "0"))
    ng = int(gold)
    ns = int(silver)
    gd = ng - pg
    sd = ns - ps

    if gold != state["gold"] or silver != state["silver"]:
        state["gold"] = gold
        state["silver"] = silver
        state["date"] = ts[:10]
        save_state(state)
        g_msg = "UP Rs." + format(abs(gd), ",") if gd > 0 else "DOWN Rs." + format(abs(gd), ",") if gd < 0 else "same"
        s_msg = "UP Rs." + format(abs(sd), ",") if sd > 0 else "DOWN Rs." + format(abs(sd), ",") if sd < 0 else "same"
        print("[" + ts + "] Changed — gold: " + g_msg + ", silver: " + s_msg)
        send_ntfy(gold, silver, str(pg), str(ps), gd, sd)
    else:
        print("[" + ts + "] No change — gold: Rs." + gold + ", silver: Rs." + silver)

    print("[" + ts + "] Done")


if __name__ == "__main__":
    main()
