# Monitor Ideas — GitHub Actions + ntfy.sh Pattern

**The template:** fetch → parse → diff cached state → notify via ntfy.sh

All run free on public GitHub repos. State persisted via `actions/cache`. Notifications delivered to phone via ntfy app.

---

## Deals & Shopping

| Monitor | Source | Granularity | Why |
|---------|--------|-------------|-----|
| **Amazon price tracker** | amazon.in/dp/XXX | 15-30 min | Track specific product, notify when price drops below target |
| **Myntra/Ajio sale monitor** | myntra.com / ajio.com | 15 min | New discounts in specific categories (mens footwear, electronics) |
| **Flipkart Open Box / Refurb** | flipkart.com | 5 min | New refurb stock at steep discounts |
| **CouponDunia / GrabOn** | coupondunia.in | 15 min | Fresh coupon codes for specific stores |
| **Croma / Reliance Digital** | cromaretail.com | 15 min | Price drops on electronics |
| **PS5 / GPU / Console restock** | Amazon/Flipkart product page | 5 min | Notify when "Add to Cart" appears |

## Jobs (BTech 2026 grad focus)

| Monitor | Source | Granularity | Why |
|---------|--------|-------------|-----|
| **LinkedIn jobs — SDE/QA** | linkedin.com/jobs | 15 min | New postings matching your keywords |
| **Naukri / Indeed — QA roles** | naukri.com / indeed.co.in | 15 min | Fresh QA/SDE openings |
| **Internshala** | internshala.com | 30 min | New internships matching skills |
| **Microsoft / Google / Amazon careers** | careers.microsoft.com etc. | 1h | New entry-level openings in India |
| **HackerNews "Who is Hiring"** | news.ycombinator.com/item?id=... | when thread drops (monthly) | Remote/India-friendly job posts |
| **AngelList / Wellfound** | angel.co | 1h | Startup jobs matching profile |

## Exams & Education

| Monitor | Source | Granularity | Why |
|---------|--------|-------------|-----|
| **NTA exam notifications** | nta.ac.in | 4h | New exam dates, results, application windows |
| **UGC NET / GATE** | ugcnet.nta.nic.in / gate.iit*.ac.in | 4h | New notifications, admit cards, results |
| **JEE / NEET / CUET** | jeemain.nta.nic.in | 4h | Result announcements, counseling dates |
| **University result portal** | your university site | 1h | When semester results are published |
| **AICTE / UGC** | ugc.ac.in | 1d | Scholarship deadlines, academic calendar |

## Finance

| Monitor | Source | Granularity | Why |
|---------|--------|-------------|-----|
| **IPO allotment status** | registrar sites (linkintime, karvy) | 15 min on IPO day | Check PAN for allotment |
| **Nifty / Bank Nifty levels** | moneypcontrol.com / nseindia.com | 1h | Opening/closing alerts, support/resistance breaks |
| **USD/INR rate** | xe.com | 1h | Currency rate change alerts |
| **FD / RD interest rates** | bank sites | 1d | New higher-rate FD offers |
| **Gold/Silver** | ✅ Already done | 2x daily | ✅ Already running |

## Content & Social

| Monitor | Source | Granularity | Why |
|---------|--------|-------------|-----|
| **YouTube — new video** | youtube.com/@channel | 15 min | New uploads from specific channels (tech reviews, courses) |
| **Twitter/X — new tweet** | x.com/handle | 5 min | New tweets from specific accounts |
| **Reddit — new post** | reddit.com/r/subreddit | 5 min | New posts matching keywords or from specific subs |
| **Medium / Dev.to** | medium.com / dev.to | 15 min | New articles matching keywords (react, python, QA) |
| **HackerNews front page** | news.ycombinator.com | 5 min | Stories that hit front page with specific keywords |
| **ProductHunt** | producthunt.com | 1h | New products launched today matching keywords |

## Availability & Restocks

| Monitor | Source | Granularity | Why |
|---------|--------|-------------|-----|
| **Railway Tatkal** | irctc.co.in | 1 min on Tatkal day | Booking window opens |
| **Bus tickets (redBus)** | redbus.in | 30 min | New routes or seats released |
| **Movie ticket shows** | bookmyshow.com | 1h | New shows at your PVR/INOX |
| **Flight fare drop** | cleartrip.com | 1h | Price drops for specific routes |
| **PS5 / Xbox / GPU** | Amazon/Flipkart product page | 5 min | "In Stock" detection |

## General & Utility

| Monitor | Source | Granularity | Why |
|---------|--------|-------------|-----|
| **Website change detector** | any URL | 1h | Generic — notify on any HTML change (govt notices, college site) |
| **API health checker** | your deployed API | 5 min | Alert when 5xx responses detected |
| **SSL cert expiry** | your domain | 1d | Notify when < 30 days to expiry |
| **IP address change** | ifconfig.me | 1h | For home servers, dynamic DNS |
| **Cricket score** | espncricinfo.com | 1 min | Live match updates |
| **Electricity / water bill** | utility portal | 1d | New bill generated notification |
| **Petrol / diesel price** | iocl.com | 1d | Daily price change in your city |
| **Weather alerts** | mausam.imd.gov.in | 1h | Rain/storm warnings for your district |

---

## Implementation notes

**Every monitor follows the exact same structure:**

```
.github/workflows/<name>.yml   → cron + cache + ntfy
<name>.py                       → fetch + parse + diff + notify
```

**State** is always a small JSON with `{date, value, first_run}` cached via `actions/cache/restore@v4` + `actions/cache/save@v4`.

**ntfy.sh** uses HTTP headers for title/priority/tags — plain text body, never JSON payload.

**Cron gotcha:** GitHub Actions minimum schedule interval is 5 min. For 1-min polling, use the 5-workflow stagger pattern.

**Cost:** $0. Public repo == unlimited Actions minutes. State cache fits in free tier (10GB/repo).
