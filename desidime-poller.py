#!/usr/bin/env python3
"""
DesiDime Deal Poller - for GitHub Actions.
Polls desidime.com/new and tracks last seen deal ID via a state file.
Detects new deals and prints alerts.
"""

import json
import os
import re
import sys
import urllib.request
import urllib.parse
from datetime import datetime, timezone

STATE_FILE = "state.json"
POLL_URL = "https://www.desidime.com/new"



PRIORITY_STORES = ["swiggy", "instamart", "flipkart", "flipkart minutes", "jiomart",
                       "zepto", "blinkit", "bbdaily", "bigbasket"]


def should_notify(deal):
    """Check if deal passes notification threshold."""
    store = (deal.get("store") or "").lower()
    title = (deal.get("title") or "").lower()

    # Priority stores: notify immediately regardless of hotness
    for s in PRIORITY_STORES:
        if s in store or s in title:
            return True

    # Otherwise: hotness >= 100
    hotness_str = deal.get("hotness") or "0"
    try:
        hotness = int(hotness_str.replace("\u00b0", "").replace("°", ""))
    except ValueError:
        hotness = 0
    return hotness >= 100


def send_ntfy_notification(deal):
    """Send notification to ntfy.sh topic if deal passes filters."""
    topic = os.environ.get("NTFY_TOPIC", "")
    if not topic or not should_notify(deal):
        return

    store_lower = deal.get("store", "").lower()
    title_lower = deal.get("title", "").lower()
    is_priority = any(s in store_lower or s in title_lower for s in PRIORITY_STORES)

    priority = 5 if is_priority else 3
    tags = ["fire", "moneybag"] if not is_priority else ["fire", "moneybag", "star"]

    title = f"New Deal: {deal['title'][:80]}"
    body = []
    if deal["price"]:
        body.append(f"Price: {deal['price']}")
    if deal["store"]:
        body.append(f"Store: {deal['store']}")
    body.append(deal["url"])
    if deal["hotness"]:
        body.append(f"Hotness: {deal['hotness']} | Comments: {deal['comments']}")
    message = "\n".join(body)

    # ntfy uses HTTP headers for metadata (title, priority, tags)
    # and POST body for message text
    headers = {
        "Title": title,
        "Priority": str(priority),
        "Tags": ",".join(tags),
    }
    data = message.encode()

    req = urllib.request.Request(
        f"https://ntfy.sh/{topic}",
        data=data,
        headers=headers,
    )
    try:
        urllib.request.urlopen(req, timeout=5)
        print(f"  ntfy sent to /{topic} (priority={priority})")
    except Exception as e:
        print(f"  ntfy failed: {e}")



def fetch_page(url):
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.read().decode("utf-8", errors="replace")


def extract_deal_details(html):
    deals = []
    articles = re.findall(r'<article[^>]*>(.*?)</article>', html, re.DOTALL)

    for article_html in articles:
        id_match = re.search(r'href="/deals/[a-z0-9-]+-(\d+)(?:[?#]|")', article_html)
        if not id_match:
            continue
        deal_id = int(id_match.group(1))

        title_match = re.search(
            r'<a[^>]*href="/deals/[^"]*"[^>]*class="[^"]*line-clamp-3[^"]*"[^>]*>(.*?)</a>',
            article_html, re.DOTALL
        )
        if not title_match:
            title_match = re.search(
                r'<a[^>]*href="/deals/[^"]*"[^>]*>(.*?)</a>',
                article_html, re.DOTALL
            )

        title = ""
        if title_match:
            title = re.sub(r'<[^>]+>', '', title_match.group(1)).strip()
            title = title.replace('&#x27;', "'").replace('&amp;', '&')
            title = title.replace('&lt;', '<').replace('&gt;', '>')
            title = re.sub(r'^\d+°\s*', '', title)

        price_match = re.search(r'₹\s*([\d,]+(?:\.\d+)?)', article_html)
        price = "₹" + price_match.group(1) if price_match else ""

        hotness_match = re.search(r'(\d+)°', article_html)
        hotness = hotness_match.group(1) + "°" if hotness_match else ""

        time_match = re.search(r'(about\s+)?(\d+\s+(minute|hour|day|second)s?\s+ago)', article_html)
        time_ago = time_match.group(0) if time_match else ""

        store_match = re.search(r'href="/groups/[^"]*"[^>]*>\s*([^<]+)\s*<', article_html)
        store = store_match.group(1).strip() if store_match else ""

        comment_match = re.search(r'>(\d+)\s*</a>\s*[^<]*comment', article_html, re.IGNORECASE)
        comment_count = int(comment_match.group(1)) if comment_match else 0

        url_match = re.search(r'href="(/deals/[a-z0-9-]+-\d+)"', article_html)
        deal_url = "https://www.desidime.com" + url_match.group(1) if url_match else ""

        deals.append({
            "id": deal_id,
            "title": title,
            "price": price,
            "url": deal_url,
            "hotness": hotness,
            "time_ago": time_ago,
            "store": store,
            "comments": comment_count,
        })

    return deals


def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {"last_seen_id": 0, "first_run": True}


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)


def main():
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    print(f"[{ts}] DesiDime Poller starting")

    state = load_state()
    print(f"[{ts}] State: last_seen_id={state.get('last_seen_id')}, first_run={state.get('first_run')}")

    try:
        html = fetch_page(POLL_URL)
    except Exception as e:
        print(f"[{ts}] Fetch failed: {e}")
        sys.exit(1)

    deals = extract_deal_details(html)
    if not deals:
        print(f"[{ts}] No deals parsed")
        sys.exit(0)

    deals.sort(key=lambda d: d["id"], reverse=True)
    max_id = max(d["id"] for d in deals)
    print(f"[{ts}] Parsed {len(deals)} deals, max ID: #{max_id}")

    new_deals = []

    if state.get("first_run"):
        state["last_seen_id"] = max_id
        state["first_run"] = False
        print(f"[{ts}] First run — initialized at #{max_id}")
    else:
        last_id = state.get("last_seen_id", 0)
        for d in deals:
            if d["id"] > last_id:
                new_deals.append(d)
            else:
                break

        if new_deals:
            new_max = max(d["id"] for d in new_deals)
            state["last_seen_id"] = new_max
            print(f"[{ts}] ** {len(new_deals)} NEW DEAL(S) FOUND **")
            for d in new_deals:
                will_notify = should_notify(d)
                sep = "=" * 60
                print(f"\n{sep}")
                print(f"  NEW DEAL! #{d['id']}" + (" [NOTIFYING]" if will_notify else " [skipped: low hotness]"))
                print(f"  {d['title']}")
                if d['price']:
                    print(f"  Price: {d['price']}")
                if d['store']:
                    print(f"  Store: {d['store']}")
                print(f"  {d['url']}")
                print(f"  Hotness: {d['hotness']} | Comments: {d['comments']}")
                if d['time_ago']:
                    print(f"  Posted: {d['time_ago']}")
                print(sep)
                if will_notify:
                    send_ntfy_notification(d)
        else:
            print(f"[{ts}] No new deals. Latest: #{last_id}")

    save_state(state)
    print(f"[{ts}] Done")
    return 0 if not new_deals else 0  # always exit 0


if __name__ == "__main__":
    sys.exit(main())