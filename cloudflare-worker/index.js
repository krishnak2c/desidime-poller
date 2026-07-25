export default {
  async scheduled(event, env, ctx) {
    const cron = event.cron;
    let eventType = cron === "*/5 * * * *" ? "desidime-poll" : "gold-silver-check";

    const resp = await fetch(
      "https://api.github.com/repos/krishnak2c/desidime-poller/dispatches",
      {
        method: "POST",
        headers: {
          Authorization: "Bearer " + env.GH_TOKEN,
          "Content-Type": "application/json",
          Accept: "application/vnd.github+json",
          "User-Agent": "cloudflare-worker-gh-dispatch",
        },
        body: JSON.stringify({ event_type: eventType }),
      }
    );
    console.log(eventType + ": " + resp.status);
  },

  async fetch(req, env, ctx) {
    const url = new URL(req.url);
    const eventType = url.searchParams.get("type") || "desidime-poll";

    const resp = await fetch(
      "https://api.github.com/repos/krishnak2c/desidime-poller/dispatches",
      {
        method: "POST",
        headers: {
          Authorization: "Bearer " + env.GH_TOKEN,
          "Content-Type": "application/json",
          Accept: "application/vnd.github+json",
          "User-Agent": "cloudflare-worker-gh-dispatch",
        },
        body: JSON.stringify({ event_type: eventType }),
      }
    );

    return new Response(eventType + ": " + resp.status + " " + (await resp.text()));
  },
};
