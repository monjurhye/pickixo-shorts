"""Claude writes each video's script, then a second Claude call reviews it
(the automated quality gate that replaces manual approval)."""

import json
import re

SCRIPT_SCHEMA = {
    "type": "object",
    "properties": {
        "topic": {"type": "string"},
        "title": {"type": "string"},
        "hook": {"type": "string"},
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "benefit": {"type": "string"},
                    "amazon_search": {"type": "string"},
                },
                "required": ["name", "benefit", "amazon_search"],
                "additionalProperties": False,
            },
        },
        "cta": {"type": "string"},
        "description": {"type": "string"},
        "stock_queries": {"type": "array", "items": {"type": "string"}},
        "hashtags": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["topic", "title", "hook", "items", "cta", "description",
                 "stock_queries", "hashtags"],
    "additionalProperties": False,
}

REVIEW_SCHEMA = {
    "type": "object",
    "properties": {
        "approved": {"type": "boolean"},
        "issues": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["approved", "issues"],
    "additionalProperties": False,
}

WRITER_SYSTEM = """You write scripts for short vertical videos (YouTube Shorts) for an Amazon \
affiliate channel aimed at US shoppers. The video is a slideshow of stock footage with \
large on-screen text; there is no voiceover and no product photos.

Each video presents a small list of useful product TYPES (generic, widely sold on Amazon, \
e.g. "magnetic spice rack", not a specific brand or listing). Viewers tap a link that \
opens an Amazon search for each item.

Rules you must follow:
- Never state a specific price or a discount. "Under $30" style budget framing is fine \
only if the whole niche is about that budget.
- No fake urgency: never "today only", "flash sale", "limited time", "selling out".
- No health, medical, safety or weight-loss claims; no claims about other people or brands.
- Only product types that genuinely exist and are commonly sold on Amazon.
- Plain, friendly American English. On-screen lines must be short: hook <= 8 words, \
item name <= 5 words, benefit <= 9 words, CTA <= 8 words.
- The title is honest about what the video shows (<= 70 characters, no clickbait lies).
- amazon_search is the search phrase a shopper would type to find that item.
- stock_queries: 3-5 short phrases describing calm stock footage that fits the mood \
(scenes, not products), e.g. "tidy kitchen counter".
- description: 1-2 sentences, no links (links are added automatically).
- hashtags: 3-5, without spaces, each starting with #, including #shorts.
- Pick a topic different from the recent topics listed."""

REVIEWER_SYSTEM = """You are the compliance and quality reviewer for an automated Amazon \
affiliate Shorts channel. Approve only if ALL are true:
1. No specific prices, discounts, or fake urgency ("today only", "flash sale", "limited time", \
"selling out", "deal of the day").
2. No health, medical, safety, or weight-loss claims; nothing about real people or brands' \
reputations.
3. Every item is a real, common product type that a shopper can find with its search phrase.
4. Title and hook are honest about the content (no bait-and-switch).
5. Text is family-friendly, grammatical English and short enough for on-screen reading.
6. The topic is not a near-duplicate of the recent topics.
List each problem you find in issues. If approved is false, issues must not be empty."""


def _client():
    import anthropic  # imported lazily so --dry-run works without the SDK installed
    return anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env


def _call_json(system, user, schema, cfg, max_tokens=4000):
    """Dispatch to the configured provider ("openai" or "anthropic")."""
    if cfg.get("provider", "anthropic") == "openai":
        return _call_json_openai(system, user, schema, cfg, max_tokens)
    return _call_json_anthropic(system, user, schema, cfg, max_tokens)


def _call_json_openai(system, user, schema, cfg, max_tokens):
    import openai  # imported lazily; reads OPENAI_API_KEY from env
    client = openai.OpenAI()
    params = dict(
        model=cfg.get("openai_model", "gpt-5-nano"),
        instructions=system,
        input=user,
        # reasoning models spend part of this budget on hidden reasoning
        max_output_tokens=max_tokens * 2,
        text={"format": {"type": "json_schema", "name": "result", "strict": True,
                         "schema": schema}},
    )
    effort = cfg.get("openai_reasoning_effort")
    try:
        try:
            resp = client.responses.create(
                reasoning={"effort": effort}, **params) if effort else client.responses.create(**params)
        except openai.BadRequestError as e:
            if effort and "reasoning" in str(e).lower():
                resp = client.responses.create(**params)  # model doesn't take this effort
            else:
                raise
    except openai.RateLimitError as e:
        raise RuntimeError("OpenAI rate limited / out of credit: {0}".format(e))
    except openai.APIStatusError as e:
        raise RuntimeError("OpenAI API error {0}: {1}".format(e.status_code, e))
    except openai.APIConnectionError:
        raise RuntimeError("OpenAI network error")

    if getattr(resp, "status", "") == "incomplete":
        raise RuntimeError("OpenAI output incomplete: {0}".format(
            getattr(resp, "incomplete_details", "")))
    text = resp.output_text or ""
    if not text.strip():
        raise RuntimeError("OpenAI returned no text (possibly a refusal)")
    return json.loads(text)


def _call_json_anthropic(system, user, schema, cfg, max_tokens=4000):
    import anthropic
    client = _client()
    model = cfg.get("model", "claude-opus-5-5")
    params = dict(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
        output_config={
            "effort": cfg.get("effort", "medium"),
            "format": {"type": "json_schema", "schema": schema},
        },
    )
    try:
        if "haiku" in model:
            # Haiku has no server-side refusal fallback; a refusal just skips the video
            resp = client.messages.create(**params)
        else:
            resp = client.beta.messages.create(
                betas=["server-side-fallback-2026-07-01"], fallbacks="default", **params)
    except anthropic.RateLimitError as e:
        raise RuntimeError("Claude rate limited: {0}".format(e.message))
    except anthropic.APIStatusError as e:
        raise RuntimeError("Claude API error {0}: {1}".format(e.status_code, e.message))
    except anthropic.APIConnectionError:
        raise RuntimeError("Claude network error")

    if resp.stop_reason == "refusal":
        raise RuntimeError("Claude declined this request")
    if resp.stop_reason == "max_tokens":
        raise RuntimeError("Claude output was cut off (max_tokens)")
    text = next((b.text for b in resp.content if b.type == "text"), "")
    return json.loads(text)


def write_script(channel, recent_topics, cfg):
    n = int(cfg.get("items_per_video", 4))
    user = (
        "Channel niche: {niche}\n"
        "Number of items: exactly {n}\n"
        "Recent topics to avoid:\n{recent}\n\n"
        "Write the next video's script."
    ).format(niche=channel["niche"], n=n,
             recent="\n".join("- " + t for t in recent_topics[-30:]) or "- (none yet)")
    script = _call_json(WRITER_SYSTEM, user, SCRIPT_SCHEMA, cfg)
    script["items"] = script["items"][:n]
    if len(script["items"]) < 2:
        raise RuntimeError("script has too few items")
    return script


def review_script(channel, script, recent_topics, cfg):
    user = "Channel niche: {0}\nRecent topics:\n{1}\n\nScript JSON:\n{2}".format(
        channel["niche"],
        "\n".join("- " + t for t in recent_topics[-30:]) or "- (none yet)",
        json.dumps(script, indent=2, ensure_ascii=False))
    verdict = _call_json(REVIEWER_SYSTEM, user, REVIEW_SCHEMA, cfg, max_tokens=2000)
    issues = local_checks(script)
    if issues:
        verdict["approved"] = False
        verdict["issues"] = list(verdict.get("issues", [])) + issues
    return verdict


BANNED = ["today only", "flash sale", "limited time", "selling out", "deal of the day",
          "% off", "cure", "guaranteed", "lose weight"]
# a dollar amount is only allowed as budget framing: "under $30" / "below $25"
PRICE_RE = re.compile(r"(?<!under )(?<!below )\$\s?\d")


def local_checks(script):
    """Cheap deterministic backstop for the reviewer."""
    issues = []
    fields = [script.get("title", ""), script.get("hook", ""), script.get("cta", ""),
              script.get("description", "")]
    for it in script.get("items", []):
        fields += [it.get("name", ""), it.get("benefit", "")]
    blob = " ".join(fields).lower()
    for b in BANNED:
        if b in blob:
            issues.append("banned phrase: {0!r}".format(b))
    if PRICE_RE.search(blob):
        issues.append("specific price mentioned")
    if len(script.get("title", "")) > 100:
        issues.append("title too long")
    return issues


def sample_script(channel, cfg):
    """Fixed script for --dry-run (no API calls)."""
    return {
        "topic": "space-saving kitchen helpers",
        "title": "4 Kitchen Helpers That Save Counter Space",
        "hook": "Tiny kitchen? Try these",
        "items": [
            {"name": "Magnetic spice rack", "benefit": "Frees a whole cabinet shelf",
             "amazon_search": "magnetic spice rack for fridge"},
            {"name": "Over-sink cutting board", "benefit": "Turns your sink into prep space",
             "amazon_search": "over the sink cutting board"},
            {"name": "Stackable pantry bins", "benefit": "See every snack at a glance",
             "amazon_search": "stackable clear pantry bins"},
            {"name": "Collapsible colander", "benefit": "Folds flat into any drawer",
             "amazon_search": "collapsible silicone colander"},
        ][: int(cfg.get("items_per_video", 4))],
        "cta": "All links on Pickixo",
        "description": "Four simple helpers that make a small kitchen feel bigger.",
        "stock_queries": ["tidy kitchen counter", "cooking at home"],
        "hashtags": ["#shorts", "#kitchenhacks", "#amazonfinds"],
    }
