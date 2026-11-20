"""Daily Pinterest pins: AliExpress hot products -> pin text -> scheduled through Buffer.

  python -m pipeline.run_pins            # schedule today's pins
  python -m pipeline.run_pins --dry-run  # sample products, no API calls, nothing posted
  python -m pipeline.run_pins --setup    # list Buffer organizations, channels and boards
"""

import argparse
import os
import re
from datetime import datetime, timedelta, timezone

from . import aliexpress, buffer, common, content, dashboard, report

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


def board_name(cfg, keyword):
    return next((b for b, kws in cfg.get("boards", {}).items() if keyword in kws), cfg.get("default_board", ""))


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
                boards = buffer.pinterest_boards(org["id"], ch["id"])
                for b in boards:
                    print("    board {0}  {1}".format(b["serviceId"], b["name"]))
                if not boards:
                    print("    no boards found; schema hints:")
                    for t in ("ChannelMetadata", "PinterestMetadata", "PinterestBoard"):
                        try:
                            d = buffer.gql('query($n:String!){ __type(name:$n){ kind possibleTypes{name} '
                                           'fields{name type{name kind ofType{name kind}}} } }', {"n": t})
                            print("     ", t, d.get("__type"))
                        except buffer.BufferError as e:
                            print("     ", t, "error:", e)
                    try:
                        d = buffer.gql("""query($org: OrganizationId!) { channels(input: {organizationId: $org})
                            { id metadata { __typename } } }""", {"org": org["id"]})
                        print("      metadata types:", d)
                    except buffer.BufferError as e:
                        print("      metadata error:", e)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--setup", action="store_true")
    ap.add_argument("--test-ali", action="store_true", help="only fetch AliExpress products, post nothing")
    ap.add_argument("--test-one", action="store_true", help="schedule just 1 real pin ~15 minutes from now")
    ap.add_argument("--test-impact", action="store_true", help="list Impact programs and catalogs")
    ap.add_argument("--sync-dashboard", action="store_true", help="send already posted pins to the dashboard")
    args = ap.parse_args()
    if args.setup:
        return setup()
    if args.test_impact:
        from . import impact
        camps = impact.campaigns()
        common.log("Impact OK: {0} joined programs".format(len(camps)))
        for c in camps:
            common.log("  program {0} | {1} | {2}".format(c.get("CampaignId"), c.get("CampaignName"),
                                                         c.get("ContractStatus") or c.get("Status") or ""))
        try:
            from collections import defaultdict
            now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            acts = impact.get("/Actions", ActionDateStart="2026-01-01T00:00:00Z", ActionDateEnd=now,
                              PageSize=1000).get("Actions", [])
            agg = defaultdict(lambda: [0, 0.0, 0.0])
            for a in acts:
                k = a.get("CampaignName") or a.get("CampaignId")
                agg[k][0] += 1
                agg[k][1] += float(a.get("Amount") or 0)
                agg[k][2] += float(a.get("Payout") or 0)
            common.log("2026 sales: {0} actions".format(len(acts)))
            for k, v in sorted(agg.items(), key=lambda kv: -kv[1][2]):
                common.log("  sales {0} | {1} actions | sale amount {2:.2f} | your commission {3:.2f}".format(k, *v))
        except impact.ImpactError as e:
            common.log("2026 sales error: {0}".format(e))
        cats = impact.catalogs()
        common.log("{0} catalogs".format(len(cats)))
        for c in cats:
            common.log("  catalog {0} | {1} | {2} | items {3}".format(
                c.get("Id"), c.get("CampaignName") or c.get("AdvertiserName"), c.get("Name"),
                c.get("NumberOfItems") or c.get("ItemCount") or "?"))
        for path in ("/Deals", "/Ads", "/PromoCodes"):
            try:
                r = impact.get(path, CampaignId=7443, PageSize=10)
                key = [k for k in r if isinstance(r[k], list)]
                rows = r.get(key[0], []) if key else []
                common.log("  appsumo {0}: {1} rows, keys {2}".format(path, len(rows),
                           ",".join(sorted(rows[0].keys())) if rows else "-"))
                for it in rows[:6]:
                    common.log("    {0} | {1} | {2} | {3}".format(
                        str(it.get("Name"))[:60], str(it.get("Description") or it.get("Type") or "")[:60],
                        str(it.get("LandingPageUrl") or it.get("LandingPage") or it.get("DefaultLandingPageUrl") or "")[:70],
                        str(it.get("TrackingLink") or it.get("Url") or "")[:50]))
            except impact.ImpactError as e:
                common.log("  appsumo {0} error: {1}".format(path, e))
        if False:
            items = impact.catalog_items(cats[0]["Id"], 3)
            for it in items:
                common.log("  sample item | {0} | img {1} | link {2}".format(
                    str(it.get("Name"))[:60], bool(it.get("ImageUrl")), str(it.get("Url"))[:45]))
        return
    if args.sync_dashboard:
        st = common.load_json(STATE, {"posted": {}})
        rows = [dict(status="scheduled", keyword=v.get("keyword", ""), product=v.get("title", ""),
                     title=v.get("title", ""), board=v.get("board", ""), due=v.get("due", v.get("date", "")),
                     link=v.get("link", ""), note="") for v in st["posted"].values() if v.get("buffer_id")]
        dashboard.pins_report({"date": common.today_utc(), "want": len(rows), "rows": rows,
                               "message": "Synced {0} earlier pin(s).".format(len(rows))})
        common.log("synced {0} pins".format(len(rows)))
        return
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
        if os.environ.get("PINS_PAUSED", "").lower() == "true" or not cfg.get("enabled") \
                or (dashboard.enabled() and dashboard.pins_paused()):
            common.log("pins paused")
            if dashboard.enabled():
                dashboard.pins_report({"date": date, "want": 0, "rows": [], "message": "Paused, nothing posted."})
            return
        missing = [n for n, ok in (("ALIEXPRESS keys", aliexpress.enabled()),
                                   ("BUFFER_API_KEY", buffer.enabled()),
                                   ("buffer_channel_id", cfg.get("buffer_channel_id")),
                                   ("buffer_organization_id", cfg.get("buffer_organization_id"))) if not ok]
        if missing:
            if dashboard.enabled():
                dashboard.pins_report({"date": date, "want": 0, "rows": [],
                                       "message": "Not set up, missing: " + ", ".join(missing)})
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
    want = 1 if args.test_one else int(cfg.get("pins_per_day", 6))
    prods = sample_products() if args.dry_run else pick_products(cfg, st, want)

    start = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    start = max(start.replace(hour=int(cfg.get("first_pin_utc_hour", 13))), start + timedelta(hours=1))
    if args.test_one:
        start = datetime.now(timezone.utc).replace(second=0, microsecond=0) + timedelta(minutes=15)
    rows = []
    for i, p in enumerate(prods):
        row = {"keyword": p["keyword"], "product": p["title"][:60], "status": "", "note": "",
               "title": "", "board": "", "due": "", "link": p.get("link", "")}
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
            st["posted"][p["id"]] = {"date": date, "title": pin["title"], "buffer_id": post.get("id"),
                                     "keyword": p["keyword"], "board": board_name(cfg, p["keyword"]),
                                     "due": due.strftime("%Y-%m-%dT%H:%M:%SZ"), "link": p["link"]}
            row.update(status="scheduled", note=due.strftime("%H:%M UTC"), title=pin["title"][:100],
                       board=board_name(cfg, p["keyword"]), due=due.strftime("%Y-%m-%dT%H:%M:%SZ"))
        except Exception as e:
            row.update(status="error", note=str(e)[:200])
            common.log("pin error: {0}".format(e))

    if args.dry_run:
        return
    common.save_json(STATE, st)
    ok = sum(1 for r in rows if r["status"] == "scheduled")
    if dashboard.enabled():
        dashboard.pins_report({"date": date, "want": want, "rows": rows})
    md = ["# Pickixo pins — {0}".format(date), "", "**Scheduled:** {0} / {1}".format(ok, want), "",
          "| Topic | Product | Status | Note |", "|---|---|---|---|"]
    md += ["| {keyword} | {product} | {status} | {note} |".format(
        **{k: str(r.get(k, "")).replace("|", "/") for k in ("keyword", "product", "status", "note")}) for r in rows]
    md += ["", "**STOP pins:** repo variable `PINS_PAUSED` = `true`."]
    report.publish("\n".join(md))


if __name__ == "__main__":
    main()
