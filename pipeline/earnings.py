"""Daily earnings collector for the dashboard (/admin -> Earnings).

Automatic income (read-only APIs):
  - AppSumo and other impact.com programs: commission (Payout) per action date
  - AliExpress affiliate: estimated commission per order date
  (AdBlueMedia arrives by itself through its postback URL -> /api/postback/adbluemedia)
Automatic costs (free admin keys, optional):
  - OpenAI: OPENAI_ADMIN_KEY (Organization Costs API)
  - Anthropic: ANTHROPIC_ADMIN_KEY (Admin API cost_report)
Amazon, Magnific and Facebook have no API; those are typed in the dashboard.

  python -m pipeline.earnings          # last 35 days -> dashboard
  python -m pipeline.earnings --print  # just print
"""

import argparse
import json
import urllib.request
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from . import aliexpress, common, dashboard, impact


def impact_by_day(start, end):
    out = defaultdict(float)
    acts = impact.get("/Actions", ActionDateStart=start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                      ActionDateEnd=end.strftime("%Y-%m-%dT%H:%M:%SZ"), PageSize=1000).get("Actions", [])
    for a in acts:
        if str(a.get("State", "")).upper() in ("REVERSED", "REJECTED"):
            continue
        day = str(a.get("EventDate") or a.get("CreationDate") or "")[:10]
        if day:
            out[day] += float(a.get("Payout") or 0)
    return out


def _find_orders(obj):
    """AliExpress wraps the list differently per method; find the list of order dicts."""
    if isinstance(obj, dict):
        for k in ("order", "orders"):
            v = obj.get(k)
            if isinstance(v, list) and v and isinstance(v[0], dict):
                return v
        for v in obj.values():
            r = _find_orders(v)
            if r:
                return r
    return []


def aliexpress_by_day(start, end):
    out = defaultdict(float)
    page = 1
    while page <= 10:
        data = aliexpress.call("aliexpress.affiliate.order.list",
                               start_time=max(start, end - timedelta(days=29)).strftime("%Y-%m-%d %H:%M:%S"),
                               end_time=end.strftime("%Y-%m-%d %H:%M:%S"),
                               status="Payment Completed", page_no=page, page_size=50)
        orders = _find_orders(data)
        for o in orders:
            day = str(o.get("created_time") or o.get("paid_time") or "")[:10]
            amt = o.get("estimated_paid_commission") or o.get("estimated_finished_commission") \
                or o.get("paid_commission") or o.get("commission") or 0
            try:
                out[day] += float(str(amt).replace("USD", "").strip() or 0)
            except ValueError:
                pass
        if len(orders) < 50:
            break
        page += 1
    return out


def _get_json(url, headers):
    req = urllib.request.Request(url, headers=dict(headers, **{"User-Agent": "pickixo-earnings"}))
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def openai_cost_by_day(start, end):
    """OpenAI Organization Costs API (needs an admin key, sk-admin-...). Amounts are USD."""
    out, page = defaultdict(float), None
    for _ in range(5):
        url = "https://api.openai.com/v1/organization/costs?bucket_width=1d&limit=31&start_time={0}&end_time={1}".format(
            int(start.timestamp()), int(end.timestamp())) + ("&page=" + page if page else "")
        d = _get_json(url, {"Authorization": "Bearer " + common.secret("OPENAI_ADMIN_KEY").strip()})
        for b in d.get("data", []):
            day = datetime.fromtimestamp(b["start_time"], timezone.utc).strftime("%Y-%m-%d")
            for r in b.get("results", []):
                out[day] += float((r.get("amount") or {}).get("value") or 0)
        page = d.get("next_page")
        if not d.get("has_more") or not page:
            break
    return out


def anthropic_cost_by_day(start, end):
    """Anthropic Admin API cost_report (needs an admin key, sk-ant-admin...). Amounts are cents."""
    out, page = defaultdict(float), None
    for _ in range(5):
        url = "https://api.anthropic.com/v1/organizations/cost_report?bucket_width=1d&limit=31&starting_at={0}&ending_at={1}".format(
            start.strftime("%Y-%m-%dT00:00:00Z"), end.strftime("%Y-%m-%dT%H:%M:%SZ")) + ("&page=" + page if page else "")
        d = _get_json(url, {"x-api-key": common.secret("ANTHROPIC_ADMIN_KEY").strip(), "anthropic-version": "2023-06-01"})
        for b in d.get("data", []):
            day = str(b.get("starting_at", ""))[:10]
            for r in b.get("results", []):
                out[day] += float(r.get("amount") or 0) / 100
        page = d.get("next_page")
        if not d.get("has_more") or not page:
            break
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--print", action="store_true")
    args = ap.parse_args()
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=35)
    days, costs, notes = defaultdict(dict), defaultdict(dict), []
    jobs = (("AppSumo (Impact)", impact_by_day, impact.enabled(), days),
            ("AliExpress", aliexpress_by_day, aliexpress.enabled(), days),
            ("OpenAI API", openai_cost_by_day, bool(common.secret("OPENAI_ADMIN_KEY")), costs),
            ("Anthropic API", anthropic_cost_by_day, bool(common.secret("ANTHROPIC_ADMIN_KEY")), costs))
    for name, fn, ok, target in jobs:
        if not ok:
            notes.append(name + ": no admin key" if target is costs else name + ": no API keys")
            continue
        try:
            for day, amt in fn(start, end).items():
                target[day][name] = round(amt, 2)
            notes.append(name + ": ok")
        except Exception as e:
            notes.append("{0}: {1}".format(name, str(e)[:120]))
    payload = {"updated": end.strftime("%Y-%m-%dT%H:%M:%SZ"), "days": days, "costs": costs, "notes": notes}
    common.log("earnings: " + "; ".join(notes))
    if args.print or not dashboard.enabled():
        print(payload)
        return
    code, data = dashboard._call("/api/pipeline/earnings", payload)
    common.log("dashboard earnings: {0} {1}".format(code, data))


if __name__ == "__main__":
    main()
