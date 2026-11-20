"""Daily earnings collector for the dashboard (/admin -> Earnings).

Automatic sources (read-only APIs we already have keys for):
  - AppSumo and other impact.com programs: commission (Payout) per action date
  - AliExpress affiliate: estimated commission per order date
Everything else (Amazon, AdBlueMedia, Magnific, Facebook, app stores, costs) is typed in the
dashboard, because those sites have no API we can use.

  python -m pipeline.earnings          # last 35 days -> dashboard
  python -m pipeline.earnings --print  # just print
"""

import argparse
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--print", action="store_true")
    args = ap.parse_args()
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=35)
    days, notes = defaultdict(dict), []
    for name, fn, ok in (("AppSumo (Impact)", impact_by_day, impact.enabled()),
                         ("AliExpress", aliexpress_by_day, aliexpress.enabled())):
        if not ok:
            notes.append(name + ": no API keys")
            continue
        try:
            for day, amt in fn(start, end).items():
                days[day][name] = round(amt, 2)
            notes.append(name + ": ok")
        except Exception as e:
            notes.append("{0}: {1}".format(name, str(e)[:120]))
    payload = {"updated": end.strftime("%Y-%m-%dT%H:%M:%SZ"), "days": days, "notes": notes}
    common.log("earnings: " + "; ".join(notes))
    if args.print or not dashboard.enabled():
        print(payload)
        return
    code, data = dashboard._call("/api/pipeline/earnings", payload)
    common.log("dashboard earnings: {0} {1}".format(code, data))


if __name__ == "__main__":
    main()
