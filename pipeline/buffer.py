"""Buffer GraphQL API (api.buffer.com) — posts Pinterest pins through the Pinterest
account connected in Buffer. Needs secret BUFFER_API_KEY (publish.buffer.com/settings/api)."""

import json
import urllib.error
import urllib.request

from . import common

API = "https://api.buffer.com"


class BufferError(Exception):
    pass


def enabled():
    return bool(common.secret("BUFFER_API_KEY"))


def gql(query, variables=None):
    body = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = urllib.request.Request(API, data=body, method="POST", headers={
        "Authorization": "Bearer " + common.secret("BUFFER_API_KEY"),
        "Content-Type": "application/json",
        "User-Agent": "pickixo-pins/1.0",
    })
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            data = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        raise BufferError("HTTP {0}: {1}".format(e.code, e.read().decode("utf-8", "ignore")[:300]))
    except Exception as e:
        raise BufferError("request failed: {0}".format(e))
    if data.get("errors"):
        raise BufferError("; ".join(str(x.get("message")) for x in data["errors"])[:400])
    return data.get("data") or {}


def organizations():
    return gql("query { account { organizations { id name } } }")["account"]["organizations"]


def channels(org_id):
    return gql("""query($org: OrganizationId!) {
      channels(input: {organizationId: $org}) {
        id name displayName service isQueuePaused isDisconnected
      }
    }""", {"org": org_id})["channels"]


def pinterest_boards(org_id, channel_id):
    data = gql("""query($org: OrganizationId!) {
      channels(input: {organizationId: $org}) {
        id
        metadata { ... on PinterestMetadata { boards { serviceId name } } }
      }
    }""", {"org": org_id})
    for ch in data["channels"]:
        if ch["id"] == channel_id:
            return (ch.get("metadata") or {}).get("boards") or []
    return []


def create_pin(channel_id, board_id, title, description, image_url, link, due_at=None):
    """Schedules a pin: at due_at (ISO UTC) if given, else the next queue slot."""
    sched = 'mode: customScheduled, dueAt: $due' if due_at else "mode: addToQueue"
    q = """mutation($ch: ChannelId!, $text: String!, $img: String!, $board: String!,
                    $title: String!, $url: String!%s) {
      createPost(input: {
        channelId: $ch, text: $text, schedulingType: automatic, %s,
        assets: [{image: {url: $img}}],
        metadata: {pinterest: {boardServiceId: $board, title: $title, url: $url}}
      }) {
        __typename
        ... on PostActionSuccess { post { id dueAt } }
        ... on InvalidInputError { message }
        ... on LimitReachedError { message }
        ... on UnauthorizedError { message }
        ... on NotFoundError { message }
        ... on UnexpectedError { message }
        ... on RestProxyError { message }
      }
    }""" % (", $due: DateTime" if due_at else "", sched)
    v = {"ch": channel_id, "text": description, "img": image_url, "board": board_id,
         "title": title, "url": link}
    if due_at:
        v["due"] = due_at
    res = gql(q, v)["createPost"]
    if res.get("__typename") != "PostActionSuccess":
        raise BufferError("{0}: {1}".format(res.get("__typename"), res.get("message")))
    return res["post"]
