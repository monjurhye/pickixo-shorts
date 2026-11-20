"""Daily Pinterest pins: AliExpress hot products -> pin text -> scheduled through Buffer.

  python -m pipeline.run_pins            # schedule today's pins
  python -m pipeline.run_pins --dry-run  # sample products, no API calls, nothing posted
  python -m pipeline.run_pins --setup    # list Buffer organizations, channels and boards
"""

import argparse
import os
import re
from datetime import datetime, timedelta, timezone

from . import aliexpress, buffer, common, content, report

CONFIG = os.path.join(common.CONFIG_DIR, "pinterest.json")
STATE = os.path.join(common.DATA_DIR, "pins.json")

PIN_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "description": {"type": "string"},
        "hashtags": {"type": "array", "items": {"type": "string"}},
        "ok": {"type": "boolean"},
    },
    "required": ["title", "description", "hashtags", "ok"],
    "additionalProperties": False,
}

PIN_SYSTEM = """You write Pinterest pins for an AliExpress affiliate account aimed at US shoppers.
Given one product's raw marketplace title, write:
- title: <= 90 characters, clear and natural, says what the product is and who it is for.
  No ALL CAPS, no emoji spam, no keyword stuffing.
- description: 1-2 friendly sentences (<= 300 characters) on what it does and why it is handy.
- hashtags: 3-5 relevant lowercase hashtags without the # sign.
- ok: false if the product looks unsafe, adult, counterfeit/branded knock-off, medical,
  weapon-related, or the title is too unclear to describe honestly; otherwise true.
Rules: never state a price, discount or shipping time; no fake urgency ("today only",
"limited", "selling out"); no health, safety or performance claims you cannot know;
never claim you personally used or reviewed it."""

BANNED = ("today only", "limited time", "selling out", "flash sale", "guaranteed", "cure",
          "free shipping", "lowest price")
PRICE_RE = re.compile(r"[$€£]\s?\d|\d+\s?(usd|dollars)|\d+\s?% off", re.I)


def load_cfg():
    return common.load_json(CONFIG, {})


def checks(pin):
    blob = (pin["title"] + " " + pin["description"]).lower()
    issues = ["banned phrase " + b for b in BANNED if b in blob]
    if PRICE_RE.search(blob):
        issues.append("price mentioned")
    if not pin.get("ok"):
        issues.append("writer flagged product")
    if len(pin["title"]) > 100:
        issues.append("title too long")
    return issues


def board_for(cfg, keyword, board_ids):
    """Board serviceId for a keyword: its mapped board, else the default board, else board_service_id."""
    name = next((b for b, kws in cfg.get("boards", {}).items() if keyword in kws), cfg.get("default_board", ""))
    return board_ids.get(name.strip().lower()) or board_ids.get(cfg.get("default_board", "").lower()) \
        or cfg.get("board_service_id", "")


def pick_products(cfg, st, want):
    kws = cfg["keywords"]
    picked, tried = [], 0
    while len(picked) < want and tried < len(kws):
        kw = kws[st["keyword_index"] % len(kws)]
        st["keyword_index"] += 1
        tried += 1
        try:
            prods = aliexpress.hot_products(kw, cfg["tracking_id"])
        except aliexpress.AliError as e:
            common.log("AliExpress {0!r}: {1}".format(kw, e))
            continue
        for p in prods:
            rate = float(str(p.get("rating") or "0").rstrip("%") or 0)
            if p["id"] in st["posted"] or rate < cfg.get("min_rating_percent", 0):
                continue
            picked.append(dict(p, keyword=kw))
            break  # one product per keyword keeps the board varied
    return picked


def sample_products():
    return [{"id": "dry1", "title": "Magnetic Spice Rack Organizer for Refrigerator",
             "image": "https://example.com/a.jpg", "link": "https://s.click.aliexpress.com/e/_x",
             "keyword": "kitchen gadgets", "rating": "96%"}]


def setup():
    for org in buffer.organizations():
        print("Organization {0}  {1}".format(org["id"], org["name"]))
        for ch in buffer.channels(org["id"]):
            print("  channel {0}  service={1}  {2}".format(ch["id"], ch["service"],
                                                           ch.get("displayName") or ch["name"]))
            if "pinterest" in str(ch["service"]).lower():
                for b in buffer.pinterest_boards(org["id"], ch["id"]):
                    print("    board {0}  {1}".format(b["serviceId"], b["name"]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--setup", action="store_true")
    ap.add_argument("--test-ali", action="store_true", help="only fetch AliExpress products, post nothing")
    args = ap.parse_args()
    if args.setup:
        return setup()
    if args.test_ali:
        cfg = load_cfg()
        prods = aliexpress.hot_products(cfg["keywords"][0], cfg["tracking_id"])
        common.log("AliExpress OK: {0} products for {1!r}".format(len(prods), cfg["keywords"][0]))
        for p in prods[:5]:
            common.log("  {0} | rating {1} | link {2}".format(p["title"][:70], p["rating"], p["link"][:40]))
        return

    cfg, ai_cfg = load_cfg(), common.settings()
    date = common.today_utc()
    if not args.dry_run:
        if os.environ.get("PINS_PAUSED", "").lower() == "true" or not cfg.get("enabled"):
            common.log("pins paused")
            return
        missing = [n for n, ok in (("ALIEXPRESS keys", aliexpress.enabled()),
                                   ("BUFFER_API_KEY", buffer.enabled()),
                                   ("buffer_channel_id", cfg.get("buffer_channel_id")),
                                   ("buffer_organization_id", cfg.get("buffer_organization_id"))) if not ok]
        if missing:
            report.publish("# Pickixo pins — {0}\n\nNot set up yet, nothing posted. Missing: {1}"
                           .format(date, ", ".join(missing)))
            return

    st = common.load_json(STATE, {"keyword_index": 0, "posted": {}})
    board_ids = {}
    if not args.dry_run:
        try:
            board_ids = {b["name"].strip().lower(): b["serviceId"] for b in
                         buffer.pinterest_boards(cfg["buffer_organization_id"], cfg["buffer_channel_id"])}
        except buffer.BufferError as e:
            common.log("could not list boards: {0}".format(e))
    want = int(cfg.get("pins_per_day", 6))
    prods = sample_products() if args.dry_run else pick_products(cfg, st, want)

    start = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    start = max(start.replace(hour=int(cfg.get("first_pin_utc_hour", 13))), start + timedelta(hours=1))
    rows = []
    for i, p in enumerate(prods):
        row = {"keyword": p["keyword"], "product": p["title"][:60], "status": "", "note": ""}
        rows.append(row)
        try:
            if args.dry_run:
                pin = {"title": "Magnetic spice rack that frees up cabinet space",
                       "description": "Sticks to the fridge and keeps spices in reach.",
                       "hashtags": ["kitchenorganization", "kitchenhacks"], "ok": True}
            else:
                pin = content._call_json(PIN_SYSTEM, "Product: " + p["title"] +
                                         "\nSearch topic: " + p["keyword"], PIN_SCHEMA, ai_cfg, 800)
            issues = checks(pin)
            if issues:
                row.update(status="skipped", note="; ".join(issues))
                st["posted"][p["id"]] = {"date": date, "skipped": True}
                continue
            tags = " ".join("#" + re.sub(r"[^a-z0-9]", "", t.lower()) for t in pin["hashtags"][:5])
            desc = "{0}\n\n{1}\n{2}".format(pin["description"].strip(), cfg["disclosure"], tags)
            due = (start + timedelta(hours=i * float(cfg.get("hours_between_pins", 2))))
            if args.dry_run:
                common.log("DRY pin: {0} | {1} | due {2}".format(pin["title"], desc, due.isoformat()))
                row.update(status="dry-run")
                continue
            board = board_for(cfg, p["keyword"], board_ids)
            if not board:
                row.update(status="error", note="no board found in Buffer for " + p["keyword"])
                continue
            post = buffer.create_pin(cfg["buffer_channel_id"], board,
                                     pin["title"][:100], desc[:500], p["image"], p["link"],
                                     due.strftime("%Y-%m-%dT%H:%M:%S.000Z"))
            st["posted"][p["id"]] = {"date": date, "title": pin["title"], "buffer_id": post.get("id")}
            row.update(status="scheduled", note=due.strftime("%H:%M UTC"))
        except Exception as e:
            row.update(status="error", note=str(e)[:200])
            common.log("pin error: {0}".format(e))

    if args.dry_run:
        return
    common.save_json(STATE, st)
    ok = sum(1 for r in rows if r["status"] == "scheduled")
    md = ["# Pickixo pins — {0}".format(date), "", "**Scheduled:** {0} / {1}".format(ok, want), "",
          "| Topic | Product | Status | Note |", "|---|---|---|---|"]
    md += ["| {keyword} | {product} | {status} | {note} |".format(
        **{k: str(v).replace("|", "/") for k, v in r.items()}) for r in rows]
    md += ["", "**STOP pins:** repo variable `PINS_PAUSED` = `true`."]
    report.publish("\n".join(md))


if __name__ == "__main__":
    main()
