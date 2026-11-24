"""AliExpress Affiliate API (Open Platform, business "sync" gateway).
Needs secrets ALIEXPRESS_APP_KEY / ALIEXPRESS_APP_SECRET from an app with the
Affiliates API permission. Product image URLs and promotion links come straight
from AliExpress, so pins never use scraped images."""

import hashlib
import hmac
import json
import time
import urllib.parse
import urllib.request

from . import common

GATEWAY = "https://api-sg.aliexpress.com/sync"


class AliError(Exception):
    pass


def enabled():
    return bool(common.secret("ALIEXPRESS_APP_KEY") and common.secret("ALIEXPRESS_APP_SECRET"))


def _sign(params, secret):
    # Business APIs: HMAC-SHA256 over the sorted key+value pairs, uppercase hex.
    base = "".join(k + str(params[k]) for k in sorted(params))
    return hmac.new(secret.encode(), base.encode(), hashlib.sha256).hexdigest().upper()


def call(method, **biz):
    params = {
        "app_key": common.secret("ALIEXPRESS_APP_KEY"),
        "method": method,
        "sign_method": "sha256",
        "timestamp": str(int(time.time() * 1000)),
        "format": "json",
        "v": "2.0",
    }
    params.update({k: str(v) for k, v in biz.items() if v not in (None, "")})
    params["sign"] = _sign(params, common.secret("ALIEXPRESS_APP_SECRET"))
    req = urllib.request.Request(
        GATEWAY, data=urllib.parse.urlencode(params).encode(), method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded;charset=utf-8",
                 "User-Agent": "pickixo-pins/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            data = json.loads(r.read().decode())
    except Exception as e:
        raise AliError("request failed: {0}".format(e))
    if "error_response" in data:
        err = data["error_response"]
        raise AliError("{0}: {1}".format(err.get("code"), err.get("msg")))
    return data


def _products(data):
    # {"aliexpress_affiliate_hotproduct_query_response": {"resp_result": {"resp_code": 200,
    #   "result": {"products": {"product": [...]}}}}}
    resp = next(iter(data.values()), {}) if data else {}
    rr = resp.get("resp_result") or {}
    if rr.get("resp_code") not in (200, "200", None):
        raise AliError("resp_code {0}: {1}".format(rr.get("resp_code"), rr.get("resp_msg")))
    prods = ((rr.get("result") or {}).get("products") or {}).get("product") or []
    return prods if isinstance(prods, list) else [prods]


def hot_products(keywords, tracking_id, page_size=20, page_no=1):
    """Best-selling products for a keyword, with affiliate promotion links."""
    data = call("aliexpress.affiliate.hotproduct.query",
                keywords=keywords, tracking_id=tracking_id, page_size=page_size,
                page_no=page_no, sort="LAST_VOLUME_DESC", target_currency="USD",
                target_language="EN", ship_to_country="US")
    out = []
    for p in _products(data):
        link = p.get("promotion_link")
        img = p.get("product_main_image_url")
        if not (link and img and p.get("product_id")):
            continue
        out.append({
            "id": str(p["product_id"]),
            "title": p.get("product_title", ""),
            "image": img,
            "link": link,
            "category": p.get("second_level_category_name") or p.get("first_level_category_name") or "",
            "rating": p.get("evaluate_rate", ""),
            "sold": p.get("lastest_volume", 0),
            "video": p.get("product_video_url") or "",
        })
    return out
