#!/usr/bin/env python3
"""Gold Rate Monitor — Haldwani 22K/1g. Polls bankbazaar, tracks change, notifies via ntfy."""

import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timezone

STATE_FILE = "gold-state.json"
GOLD_URL = "https://www.bankbazaar.com/gold-rate-haldwani.html"


def fetch_page(url):
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


def extract_22k_1g(html):
    """Parse today's 22K/1g gold rate from bankbazaar table.
    Table structure: Gram | Today | Yesterday | Change
    1 gram row has today's 22K price in second <td>."""
    m = re.search(
        r"<td[^>]*>\s*1\s*gram\s*</td>\s*"
        r"<td[^>]*>\s*<[^>]*>\s*₹\s*([\d,]+)\s*</",
        html, re.DOTALL | re.IGNORECASE
    )
    if m:
        return m.group(1).replace(",", "")
    return None


def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {"date": None, "rate": "0", "first_run": True}


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)


def send_ntfy(rate, prev_rate, desc):
    topic = os.environ.get("NTFY_TOPIC", "")
    if not topic:
        return
    title = "Gold 22K: ₹" + rate + "/g"
    body = "\n".join(filter(None, [
        "Haldwani — 22 Carat",
        "Today: ₹" + rate + "/g",
        "Prev:  ₹" + prev_rate + "/g" if prev_rate != "0" else "",
        desc,
        "https://www.bankbazaar.com/gold-rate-haldwani.html",
    ]))
    headers = {"Title": title, "Priority": "3", "Tags": "droplet"}
    req = urllib.request.Request(
        "https://ntfy.sh/" + topic, data=body.encode(), headers=headers
    )
    try:
        urllib.request.urlopen(req, timeout=5)
        print("  ntfy sent to /" + topic)
    except Exception as e:
        print("  ntfy failed: " + str(e))


def main():
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    print("[" + ts + "] Gold Monitor starting")

    state = load_state()
    print("[" + ts + "] State: first_run=" + str(state.get("first_run"))
          + ", rate=" + str(state.get("rate")))

    try:
        html = fetch_page(GOLD_URL)
    except Exception as e:
        print("[" + ts + "] Fetch failed: " + str(e))
        sys.exit(1)

    rate = extract_22k_1g(html)
    if not rate:
        print("[" + ts + "] Could not parse rate")
        sys.exit(0)

    print("[" + ts + "] 22K/1g: ₹" + rate)

    if state.get("first_run"):
        state["first_run"] = False
        state["date"] = ts[:10]
        state["rate"] = rate
        save_state(state)
        print("[" + ts + "] Initialized at ₹" + rate + "/g")
        return

    now = int(rate)
    prev = int(state.get("rate", "0"))
    diff = now - prev

    if rate != state["rate"]:
        state["rate"] = rate
        state["date"] = ts[:10]
        save_state(state)

        direction = "UP" if diff > 0 else "DOWN"
        change = "₹" + format(abs(diff), ",")
        pct = format(abs(diff) / prev * 100, ".1f") + "%" if prev else "N/A"
        desc = direction + " " + change + " (" + pct + ")"
        print("[" + ts + "] Rate changed: " + desc)
        send_ntfy(rate, str(prev), desc)
    else:
        print("[" + ts + "] No change — still ₹" + rate + "/g")

    print("[" + ts + "] Done")


if __name__ == "__main__":
    main()
