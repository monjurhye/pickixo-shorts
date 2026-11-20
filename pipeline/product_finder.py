"""Product finder agent: fills data/products.json with real Amazon products (ASINs) per
channel, fully automatic, without the Product Advertising API and without scraping Amazon.

How an ASIN is trusted: an OpenAI model uses its web_search tool to look for products on
amazon.com. A product is kept ONLY if its ASIN comes from an amazon.com URL that the search
tool itself returned (a source or a citation). An ASIN that appears only in the model's own
text is thrown away, so nothing is ever guessed. Only ASIN + a short generic name are
stored: no prices, no images, no reviews.

  python -m pipeline.product_finder              # refresh channels that need it
  python -m pipeline.product_finder --channel ch01 --force
  python -m pipeline.product_finder --dry-run    # show what would be asked, no API calls

A channel is refreshed when it has fewer than `product_finder_min` products younger than
`product_finder_max_age_days`. Older products are dropped (listings change)."""

import argparse
import os
import re
from datetime import datetime, timedelta, timezone

from . import common

AUTO_PATH = os.path.join(common.DATA_DIR, "products.json")

SCHEMA = {
    "type": "object",
    "properties": {
        "products": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "url": {"type": "string"},
                },
                "required": ["name", "url"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["products"],
    "additionalProperties": False,
}

SYSTEM = """You find real products on amazon.com (United States) for a channel of short \
"useful finds" videos. Use the web search tool and search amazon.com itself \
(for example "site:amazon.com magnetic spice rack").

Rules:
- Every product must be a real listing you saw in the search results, with its amazon.com \
product URL containing /dp/<ASIN> exactly as the search result shows it. Never type or \
change an ASIN yourself; if you did not see the URL, leave that product out.
- Pick well-reviewed, everyday products that clearly fit the niche, each a DIFFERENT \
product type. If the niche names a budget (like "under $30"), only pick products that \
are normally within it.
- No adult, weapon, medical-device, supplement, drug, or baby-sleep-safety products.
- name: the generic product type in at most 5 words, no brand (e.g. "Magnetic spice rack").
Return fewer products rather than any you are unsure about."""


def load_auto():
    return common.load_json(AUTO_PATH, None) or {"products": []}


def _today():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def fresh(products, channel_id, max_age_days):
    cutoff = (datetime.now(timezone.utc) - timedelta(days=max_age_days)).strftime("%Y-%m-%d")
    return [p for p in products if channel_id in p.get("channels", []) and p.get("found", "") >= cutoff]


def _amazon_asins(urls):
    """ASINs from amazon.com product URLs only (other shops and short links ignored)."""
    out = set()
    for u in urls:
        if not re.match(r"^https?://(?:www\.|smile\.)?amazon\.com/", u or "", re.I):
            continue
        a = common.parse_asin(u)
        if a:
            out.add(a)
    return out


def _tool_urls(resp):
    """Every URL the web_search tool returned: action sources and url citations."""
    urls = []
    for item in getattr(resp, "output", []) or []:
        kind = getattr(item, "type", "")
        if kind == "web_search_call":
            action = getattr(item, "action", None)
            for s in (getattr(action, "sources", None) or []):
                urls.append(getattr(s, "url", "") or (s.get("url", "") if isinstance(s, dict) else ""))
        elif kind == "message":
            for c in getattr(item, "content", []) or []:
                for a in getattr(c, "annotations", []) or []:
                    if getattr(a, "type", "") == "url_citation":
                        urls.append(getattr(a, "url", ""))
    return [u for u in urls if u]


def find_for_channel(channel, want, cfg, avoid_names=()):
    import json
    import openai  # lazy; reads OPENAI_API_KEY
    client = openai.OpenAI()
    user = ("Channel niche: {0}\nFind {1} products.\n{2}"
            "Return JSON only.").format(
        channel["niche"], want,
        ("Already have (pick other types): " + ", ".join(avoid_names) + "\n") if avoid_names else "")
    params = dict(
        model=cfg.get("product_finder_model", "gpt-5-nano"),
        instructions=SYSTEM,
        input=user,
        tools=[{"type": "web_search"}],
        include=["web_search_call.action.sources"],
        max_output_tokens=12000,
        text={"format": {"type": "json_schema", "name": "products", "strict": True, "schema": SCHEMA}},
    )
    effort = cfg.get("product_finder_effort", "low")
    try:
        resp = client.responses.create(reasoning={"effort": effort}, **params)
    except openai.BadRequestError as e:
        if "reasoning" in str(e).lower():
            resp = client.responses.create(**params)
        else:
            raise
    seen = _amazon_asins(_tool_urls(resp))
    try:
        data = json.loads(resp.output_text or "{}")
    except ValueError:
        data = {"products": []}
    kept, dropped = [], 0
    for p in data.get("products", []):
        asin = common.parse_asin(p.get("url", ""))
        name = " ".join((p.get("name") or "").split()[:6])
        if asin and asin in seen and name:
            kept.append({"asin": asin, "name": name})
        else:
            dropped += 1
    common.log("[{0}] product finder: {1} verified, {2} dropped (not in search results), "
               "{3} amazon urls seen".format(channel["id"], len(kept), dropped, len(seen)))
    return kept


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--channel", default="")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    cfg = common.settings()
    want = int(cfg.get("product_finder_batch", 12))
    need = int(cfg.get("product_finder_min", 8))
    max_age = int(cfg.get("product_finder_max_age_days", 30))
    max_channels = int(cfg.get("product_finder_channels_per_run", 20))

    auto = load_auto()
    # drop stale listings
    cutoff = (datetime.now(timezone.utc) - timedelta(days=max_age)).strftime("%Y-%m-%d")
    auto["products"] = [p for p in auto["products"] if p.get("found", "") >= cutoff]

    done = 0
    for ch in common.channels():
        if args.channel and ch["id"] != args.channel:
            continue
        have = fresh(auto["products"], ch["id"], max_age)
        if len(have) >= need and not args.force:
            continue
        if done >= max_channels:
            break
        if args.dry_run:
            common.log("[{0}] would search: {1} (has {2})".format(ch["id"], ch["niche"], len(have)))
            continue
        try:
            found = find_for_channel(ch, want, cfg, [p["name"] for p in have])
        except Exception as e:
            common.log("[{0}] product finder failed: {1}".format(ch["id"], str(e)[:200]))
            continue
        done += 1
        known = {p["asin"] for p in have}
        for p in found:
            if p["asin"] in known:
                continue
            known.add(p["asin"])
            auto["products"].append({"asin": p["asin"], "name": p["name"], "channels": [ch["id"]],
                                     "found": _today(), "source": "web_search"})
    if not args.dry_run:
        common.save_json(AUTO_PATH, auto)
        common.log("products.json: {0} products".format(len(auto["products"])))


if __name__ == "__main__":
    main()
