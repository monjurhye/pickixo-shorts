"""Daily orchestrator: for each enabled channel -> Claude script -> Claude review gate ->
stock clips -> render -> YouTube upload -> save record (feeds shop.pickixo.com) -> report.

  python -m pipeline.run_daily               # normal run (GitHub Actions)
  python -m pipeline.run_daily --dry-run     # sample script, no API calls, no upload
  python -m pipeline.run_daily --channel ch01 --no-upload
"""

import argparse
import os
import shutil

from . import common, content, dashboard, pexels, render, report, state, tts, youtube


def build_description(script, page_url, links, cfg):
    lines = [script["description"].strip(), "",
             "🛒 Everything from this video: " + page_url, ""]
    for it in links:
        lines.append("• {0}: {1}".format(it["name"], it["link"]))
    credits = "Stock footage: Pexels"
    if cfg.get("tts_enabled"):
        credits += " · Voice: AI-generated"
    lines += ["", cfg.get("disclosure", ""), credits, "",
              " ".join(script.get("hashtags", []))]
    return "\n".join(lines)


def item_links(items, ch):
    """Specific product page when the item's ASIN is one the owner listed for this
    channel (config/products.json); otherwise an Amazon search (never a guessed ASIN)."""
    known = {p["asin"] for p in common.products(ch["id"])}
    out = []
    for it in items:
        asin = common.parse_asin(it.get("asin", ""))
        if asin and asin in known:
            out.append(dict(it, asin=asin, link=common.amazon_product_link(asin, ch["tracking_id"])))
        else:
            out.append(dict(it, asin="", link=common.amazon_search_link(it["amazon_search"], ch["tracking_id"])))
    return out


def make_one(ch, idx, chstate, cfg, dry, no_upload, date):
    """Returns a report row. Raises nothing."""
    row = {"channel": ch.get("name") or ch["id"], "niche": ch["niche"], "status": "", "note": ""}
    work = None
    try:
        # 1. script + automated review gate (up to two rewrites, each told why the last draft failed)
        if dry:
            script = content.sample_script(ch, cfg)
        else:
            script, verdict, issues = None, None, None
            for attempt in range(3):
                script = content.write_script(ch, chstate["recent_topics"], cfg, fix_issues=issues)
                verdict = content.review_script(ch, script, chstate["recent_topics"], cfg)
                if verdict.get("approved"):
                    break
                issues = verdict.get("issues", [])
                common.log("[{0}] review rejected (try {1}): {2}".format(
                    ch["id"], attempt + 1, "; ".join(verdict.get("issues", []))))
            if not verdict.get("approved"):
                row.update(status="rejected", note="; ".join(verdict.get("issues", []))[:300])
                return row

        links = item_links(script["items"], ch)
        key = "{0}-{1}-{2}".format(date, ch["id"], common.slugify(script["topic"], 40))
        page_url = "{0}/v/{1}/".format(cfg["site_url"].rstrip("/"), key)
        work = os.path.join(common.WORK_DIR, key)
        os.makedirs(work, exist_ok=True)

        # 2. stock footage (falls back to plain backgrounds without a Pexels key)
        clip_paths, pkey, cover = [], common.secret("PEXELS_API_KEY"), {}
        if pkey and not dry:
            queries = list(script.get("stock_queries", [])) + list(ch.get("stock_queries", []))
            for c in pexels.find_clips(queries, 3, chstate["used_clips"], pkey):
                try:
                    clip_paths.append(pexels.download(c, work))
                    if not cover and c.get("image"):
                        cover = {"image": c["image"], "image_credit": c.get("page", "")}
                    state.remember_clip(chstate, c["id"])
                except Exception as e:
                    common.log("[{0}] clip download failed: {1}".format(ch["id"], e))

        # 3. voiceover (OpenAI TTS) + render
        voice_files = None
        if cfg.get("tts_enabled") and not dry and common.secret("OPENAI_API_KEY"):
            voice_files = tts.voice_scenes(script, tts.voice_for(idx, cfg), work, cfg)
        out_mp4 = os.path.join(work, key + ".mp4")
        _, seconds = render.build(script, idx, clip_paths, out_mp4, cfg,
                                  cfg.get("brand", "Pickixo Picks"), voice_files=voice_files)
        common.log("[{0}] rendered {1:.0f}s video: {2}".format(ch["id"], seconds, out_mp4))

        # 4. upload
        description = build_description(script, page_url, links, cfg)
        video_id = ""
        if dry or no_upload:
            row.update(status="built", note="not uploaded ({0})".format("dry run" if dry else "--no-upload"))
        elif not youtube.has_credentials(ch["id"]):
            row.update(status="built", note="no YouTube token yet for " + ch["id"])
        else:
            video_id = youtube.upload(ch["id"], out_mp4, script["title"], description,
                                      script.get("hashtags", []), cfg)
            chstate["upload_errors"] = 0
            row.update(status="uploaded", video_id=video_id, note=script["title"])

        # 5. record for the website (skipped on dry runs and no-upload tests)
        if not dry and not no_upload:
            state.remember_topic(chstate, script["topic"])
            common.save_json(os.path.join(common.VIDEOS_DATA_DIR, key + ".json"), {
                "key": key, "date": date, "channel_id": ch["id"],
                "channel_name": ch.get("name", ""), "niche": ch["niche"],
                "title": script["title"], "hook": script["hook"],
                "description": script["description"], "items": links,
                "youtube_id": video_id, "page_url": page_url, **cover,
            })
        if dry or no_upload:
            row["note"] += " | title: " + script["title"] + " | clips: " + str(len(clip_paths))
            work = None  # keep files for inspection / artifact
    except youtube.UploadError as e:
        chstate["last_error"] = str(e)[:300]
        if e.permanent:
            chstate["upload_errors"] += 1
            limit = int(cfg.get("auto_disable_on_upload_errors", 2))
            if chstate["upload_errors"] >= limit:
                chstate["auto_disabled"] = True
                row["note"] = "AUTO-DISABLED after {0} upload errors. ".format(limit)
                if dashboard.enabled():
                    dashboard.report(ch["id"], "Auto-paused after repeated upload errors: " + str(e)[:200],
                                     disable=True)
                    chstate["auto_disabled"] = False  # the dashboard owns the switch now
        row.update(status="upload error", note=row["note"] + str(e)[:200])
    except Exception as e:
        row.update(status="error", note=str(e)[:300])
    finally:
        if work and os.path.isdir(work):
            shutil.rmtree(work, ignore_errors=True)
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-upload", action="store_true")
    ap.add_argument("--channel", default="")
    args = ap.parse_args()

    cfg, chans, st, date = common.settings(), common.channels(), state.load(), common.today_utc()
    rows = []

    # PAUSED stops real runs; dry runs and --no-upload tests never publish, so they still run
    if os.environ.get("PAUSED", "").lower() == "true" and not (args.dry_run or args.no_upload):
        report.publish(report.markdown(date, [], "PAUSED is true — nothing was made or uploaded."))
        return

    dash = None
    if dashboard.enabled() and not (args.dry_run or args.no_upload):
        try:
            dash = dashboard.state()
        except Exception as e:
            report.publish(report.markdown(date, [], "Dashboard unreachable, nothing uploaded: " + str(e)[:200]))
            return
        if dash.get("paused"):
            report.publish(report.markdown(date, [], "Paused from the dashboard — nothing was made or uploaded."))
            return

    per_day = max(1, int(cfg.get("videos_per_channel_per_run", 1)))
    for idx, ch in enumerate(chans):
        if args.channel and ch["id"] != args.channel:
            continue
        chstate = state.ch(st, ch["id"])
        if not args.dry_run and not args.channel:
            if dash is not None:
                info = dash["channels"].get(ch["id"])
                if not info or not info.get("enabled"):
                    continue
                ch = dict(ch, name=info.get("title") or ch.get("name"))
            elif not ch.get("enabled"):
                continue
            if chstate["auto_disabled"]:
                rows.append({"channel": ch.get("name") or ch["id"], "niche": ch["niche"],
                             "status": "disabled",
                             "note": "auto-disabled: " + chstate.get("last_error", "")[:150]})
                continue
        for _ in range(per_day):
            rows.append(make_one(ch, idx, chstate, cfg, args.dry_run, args.no_upload, date))
        if not (args.dry_run or args.no_upload):
            state.save(st)  # save after each channel so a crash keeps progress

    report.publish(report.markdown(date, rows), open_issue=not (args.dry_run or args.no_upload))


if __name__ == "__main__":
    main()
