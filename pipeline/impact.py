"""impact.com Partner API (read-only credentials). Secrets IMPACT_ACCOUNT_SID /
IMPACT_AUTH_TOKEN. Lists joined programs (Campaigns) and product Catalogs."""

import base64
import json
import urllib.error
import urllib.parse
import urllib.request

from . import common

API = "https://api.impact.com/Mediapartners/{sid}"


class ImpactError(Exception):
    pass


def enabled():
    return bool(common.secret("IMPACT_ACCOUNT_SID") and common.secret("IMPACT_AUTH_TOKEN"))


def get(path, **params):
    sid = common.secret("IMPACT_ACCOUNT_SID").strip()
    tok = common.secret("IMPACT_AUTH_TOKEN").strip()
    bad = sum(1 for ch in sid + tok if ord(ch) > 126 or ord(ch) < 33)
    if bad:
        raise ImpactError("Impact SID/token contain {0} non-plain characters; copy them again".format(bad))
    url = API.format(sid=sid) + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    auth = base64.b64encode("{0}:{1}".format(sid, tok).encode()).decode()
    req = urllib.request.Request(url, headers={"Authorization": "Basic " + auth,
                                               "Accept": "application/json",
                                               "User-Agent": "pickixo-pins/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        raise ImpactError("HTTP {0}: {1}".format(e.code, e.read().decode("utf-8", "ignore")[:300]))
    except Exception as e:
        raise ImpactError("request failed: {0}".format(e))


def campaigns():
    return get("/Campaigns", PageSize=100).get("Campaigns", [])


def catalogs():
    return get("/Catalogs", PageSize=100).get("Catalogs", [])


def catalog_items(catalog_id, page_size=20, **filters):
    return get("/Catalogs/{0}/Items".format(catalog_id), PageSize=page_size, **filters).get("Items", [])
