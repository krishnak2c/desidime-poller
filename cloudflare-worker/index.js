const DESIDIME_URL = "https://desidime.com/new";
const NTFY_DEALS = "https://ntfy.sh/deals-notify";
const PRIORITY_STORES = ["Swiggy", "Instamart", "Flipkart", "Flipkart Minutes", "Jiomart", "Blinkit"];
const UA_HEADERS = {
  "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
  "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
};

export default {
  async scheduled(event, env, ctx) {
    const cron = event.cron;
    if (cron === "*/5 * * * *") {
      await pollDeals(env);
    } else {
      await pollRates(env);
    }
  },

  async fetch(req, env, ctx) {
    const url = new URL(req.url);
    const action = url.searchParams.get("action") || "deals";

    if (action === "deals") {
      const lastId = await env.DESIDIME_STATE.get("last_seen_id", "text") || "0";
      const result = await pollDeals(env);
      return new Response(result, { headers: { "Content-Type": "text/plain" } });
    }
    if (action === "rates") {
      const result = await pollRates(env);
      return new Response(result, { headers: { "Content-Type": "text/plain" } });
    }
    if (action === "status") {
      const lastId = await env.DESIDIME_STATE.get("last_seen_id", "text") || "none";
      const gold = await env.DESIDIME_STATE.get("gold_rate", "text") || "none";
      const silver = await env.DESIDIME_STATE.get("silver_rate", "text") || "none";
      return new Response(`last_seen_id: ${lastId}\ngold: ${gold}\nsilver: ${silver}`, {
        headers: { "Content-Type": "text/plain" }
      });
    }

    return new Response("unknown action", { status: 400 });
  }
};

async function pollDeals(env) {
  const r = await fetch(DESIDIME_URL, { headers: UA_HEADERS });
  const html = await r.text();

  const deals = [];
  const articleRegex = /<article[^>]*deal-card[^>]*>[\s\S]*?<\/article>/g;
  let m;
  while ((m = articleRegex.exec(html)) !== null) {
    const a = m[0];
    const id = (a.match(/data-gtm-deal-id="(\d+)"/) || [])[1];
    if (!id) continue;

    const title = (a.match(/<h2[^>]*>([^<]+)/) || [])[1] || "?";
    const store = (a.match(/data-gtm-store="([^"]+)"/) || [])[1] || "?";
    const prices = [...a.matchAll(/[₹]\s*([\d,]+)/g)].map(x => x[1]);
    const hotPct = (a.match(/\((\d+)%\)/) || [])[1];
    const hotDeg = (a.match(/(\d+)\s*°/) || [])[1];
    const hotness = parseInt(hotPct || hotDeg || "0", 10);

    deals.push({ id: parseInt(id, 10), title: title.trim().slice(0, 80), price: prices[0] || "?", store, hotness });
  }

  if (deals.length === 0) return "No deals found";

  deals.sort((a, b) => b.id - a.id);
  const lastId = parseInt(await env.DESIDIME_STATE.get("last_seen_id", "text") || "0", 10);
  const newDeals = deals.filter(d => d.id > lastId);
  const maxId = deals[0].id;

  if (newDeals.length === 0) return `No new deals (max: ${maxId})`;

  let notified = 0;
  for (const d of newDeals) {
    const isPriority = PRIORITY_STORES.some(s => d.store.toLowerCase().includes(s.toLowerCase()));
    if (isPriority || d.hotness >= 100) {
      await fetch(NTFY_DEALS, {
        method: "POST",
        body: `New: ${d.title}\n₹${d.price} | ${d.store} | ${d.hotness}°\nhttps://desidime.com/deals/${d.id}`,
        headers: {
          "Title": `${d.store}: ${d.title.slice(0, 40)}`,
          "Priority": isPriority ? "5" : "3",
          "Tags": isPriority ? "star" : "shopping_cart"
        }
      });
      notified++;
    }
  }

  await env.DESIDIME_STATE.put("last_seen_id", String(maxId));
  return `New: ${newDeals.length} | Notified: ${notified} | Max ID: ${maxId}`;
}

async function pollRates(env) {
  const GOLD_URL = "https://www.bankbazaar.com/gold-rate-haldwani.html";
  const SILVER_URL = "https://www.bankbazaar.com/silver-rate-haldwani.html";
  const RATE_REGEX = /<td[^>]*>\s*1\s*gram\s*<\/td>\s*<td[^>]*>\s*<[^>]*>\s*[₹Rs]+\s*([\d,]+)\s*</i;

  const [goldRes, silverRes] = await Promise.all([
    fetch(GOLD_URL, UA_HEADERS),
    fetch(SILVER_URL, UA_HEADERS)
  ]);
  const [goldHtml, silverHtml] = await Promise.all([goldRes.text(), silverRes.text()]);

  const goldMatch = goldHtml.match(RATE_REGEX);
  const silverMatch = silverHtml.match(RATE_REGEX);
  const goldRate = goldMatch ? goldMatch[1].replace(/,/g, "") : null;
  const silverRate = silverMatch ? silverMatch[1].replace(/,/g, "") : null;

  if (!goldRate && !silverRate) {
    return "Could not parse rates";
  }

  const prevGold = await env.DESIDIME_STATE.get("gold_rate", "text") || "0";
  const prevSilver = await env.DESIDIME_STATE.get("silver_rate", "text") || "0";
  const prevDate = await env.DESIDIME_STATE.get("rates_date", "text") || "";

  const goldChanged = goldRate && goldRate !== prevGold;
  const silverChanged = silverRate && silverRate !== prevSilver;

  if (goldChanged || silverChanged) {
    const goldDiff = goldRate ? (parseInt(goldRate) - parseInt(prevGold)) : 0;
    const silverDiff = silverRate ? (parseInt(silverRate) - parseInt(prevSilver)) : 0;

    let msg = `Haldwani`;
    if (goldRate) msg += `\n22K Gold: Rs.${goldRate}/g`;
    if (prevGold !== "0") msg += ` (${goldDiff > 0 ? "UP" : "DOWN"} Rs.${Math.abs(goldDiff)})`;
    if (silverRate) msg += `\nSilver: Rs.${silverRate}/Kg`;
    if (prevSilver !== "0") msg += ` (${silverDiff > 0 ? "UP" : "DOWN"} Rs.${Math.abs(silverDiff)})`;
    msg += `\nhttps://www.bankbazaar.com/gold-rate-haldwani.html`;

    const title = goldRate && silverRate
      ? `Gold: Rs.${goldRate}/g | Silver: Rs.${silverRate}/Kg`
      : goldRate ? `Gold: Rs.${goldRate}/g` : `Silver: Rs.${silverRate}/Kg`;

    await fetch("https://ntfy.sh/gold-silver", {
      method: "POST",
      body: msg,
      headers: { "Title": title }
    });
  }

  if (goldRate) await env.DESIDIME_STATE.put("gold_rate", goldRate);
  if (silverRate) await env.DESIDIME_STATE.put("silver_rate", silverRate);
  await env.DESIDIME_STATE.put("rates_date", new Date().toISOString().slice(0, 10));

  const changes = [];
  if (goldChanged) changes.push(`gold: ${prevGold} → ${goldRate}`);
  if (silverChanged) changes.push(`silver: ${prevSilver} → ${silverRate}`);
  return changes.length ? `Changed: ${changes.join(", ")}` : "No change";
}
