"""Product finder agent: fills data/products.json with real Amazon products (ASINs) per
channel, fully automatic, without the Product Advertising API and without scraping Amazon.

How an ASIN is trusted: the model first lists generic product types for the niche, then
one web search per type ("site:amazon.com <type>"). The ASIN is taken ONLY from an
amazon.com product URL that the search tool itself returned (a source or a citation),
never from the model's own text, so nothing is ever guessed. Only ASIN + a short generic name are
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
        if not re.match(r"^https?://(?:www\.|smile\.|us\.)?amazon\.com/", u or "", re.I):
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


TYPES_SCHEMA = {
    "type": "object",
    "properties": {"types": {"type": "array", "items": {"type": "string"}}},
    "required": ["types"],
    "additionalProperties": False,
}

TYPES_SYSTEM = """You plan products for a channel of short "useful finds" videos for US \
Amazon shoppers. List generic product TYPES (no brands), each a different everyday item \
that is widely sold on amazon.com and clearly fits the niche, at most 5 words each \
(e.g. "Magnetic spice rack"). If the niche names a budget, only types normally within it. \
No adult, weapon, medical-device, supplement, drug or baby-sleep products."""


def _responses(client, cfg, **params):
    import openai
    effort = cfg.get("product_finder_effort", "low")
    try:
        return client.responses.create(reasoning={"effort": effort}, **params)
    except openai.BadRequestError as e:
        if "reasoning" in str(e).lower() or "tool_choice" in str(e).lower():
            params.pop("tool_choice", None)
            return client.responses.create(**params)
        raise


def product_types(client, channel, want, cfg, avoid_names=()):
    import json
    user = "Channel niche: {0}\nList {1} product types.\n{2}".format(
        channel["niche"], want,
        ("Already covered (pick other types): " + ", ".join(avoid_names)) if avoid_names else "")
    resp = _responses(client, cfg, model=cfg.get("product_finder_model", "gpt-5-nano"),
                      instructions=TYPES_SYSTEM, input=user, max_output_tokens=4000,
                      text={"format": {"type": "json_schema", "name": "types", "strict": True,
                                       "schema": TYPES_SCHEMA}})
    types = json.loads(resp.output_text or "{}").get("types", [])
    return [" ".join(t.split()[:6]) for t in types if t.strip()][:want]


def search_asin(client, ptype, cfg):
    """Two tries: "site:amazon.com <type>", then "<type> amazon.com/dp" (one web search each)."""
    for q in ("site:amazon.com " + ptype, ptype + " amazon.com/dp"):
        asin = _search_once(client, ptype, q, cfg)
        if asin:
            return asin
    return ""


def _search_once(client, ptype, query, cfg):
    """One web search on amazon.com for a product type. Returns the first ASIN found in an
    amazon.com product URL that the search tool returned, or ""."""
    resp = _responses(client, cfg, model=cfg.get("product_finder_model", "gpt-5-nano"),
                      instructions=("Search the web for this product on amazon.com and list the "
                                    "amazon.com product page URLs (with /dp/) you found."),
                      input=query,
                      tools=[{"type": "web_search"}], tool_choice="required",
                      include=["web_search_call.action.sources"], max_output_tokens=3000)
    urls = _tool_urls(resp)
    for u in urls:
        found = _amazon_asins([u])
        if found:
            return found.pop()
    common.log("  no amazon.com product url for {0!r} ({1} urls seen, e.g. {2})".format(
        ptype, len(urls), ", ".join(sorted({re.sub(r"^https?://([^/]+).*", r"\1", u) for u in urls})[:8])))
    am = [u for u in urls if "amazon." in u][:3]
    if am:
        common.log("  amazon urls: " + " | ".join(u[:120] for u in am))
    return ""


def find_for_channel(channel, want, cfg, avoid_names=()):
    import openai  # lazy; reads OPENAI_API_KEY
    client = openai.OpenAI()
    kept = []
    for t in product_types(client, channel, want, cfg, avoid_names):
        try:
            asin = search_asin(client, t, cfg)
        except Exception as e:
            common.log("  search failed for {0!r}: {1}".format(t, str(e)[:150]))
            continue
        if asin and asin not in {k["asin"] for k in kept}:
            kept.append({"asin": asin, "name": t})
    common.log("[{0}] product finder: {1} verified of {2} wanted".format(channel["id"], len(kept), want))
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
    for ch in [c for c in common.channels() if c.get("source") != "aliexpress"]:
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
