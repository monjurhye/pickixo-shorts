"""Daily report: written to the Actions run summary and posted as a GitHub issue,
which GitHub emails to the repo owner (set your GitHub email to monjurhye@gmail.com)."""

import json
import os
import urllib.request

from . import common


def markdown(date, rows, paused_note=""):
    ok = sum(1 for r in rows if r["status"] == "uploaded")
    from datetime import datetime, timezone
    lines = ["# Pickixo report — {0} {1}:00 UTC".format(date, datetime.now(timezone.utc).strftime("%H")), ""]
    if paused_note:
        lines += ["> " + paused_note, ""]
    lines += ["**Uploaded:** {0} / {1}".format(ok, len(rows)), "",
              "| Channel | Niche | Status | Video | Note |",
              "|---|---|---|---|---|"]
    for r in rows:
        link = "[watch](https://youtu.be/{0})".format(r["video_id"]) if r.get("video_id") else ""
        lines.append("| {0} | {1} | {2} | {3} | {4} |".format(
            r["channel"], r["niche"], r["status"], link, r.get("note", "").replace("|", "/")[:160]))
    lines += ["", "**STOP everything:** repo Settings → Secrets and variables → Actions → "
              "Variables → set `PAUSED` to `true`."]
    return "\n".join(lines)


def publish(md, open_issue=True):
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as f:
            f.write(md + "\n")
    repo, token = os.environ.get("GITHUB_REPOSITORY"), os.environ.get("GITHUB_TOKEN")
    if not (repo and token and open_issue):
        common.log("no GITHUB_TOKEN; report printed only\n" + md)
        return
    title = md.splitlines()[0].lstrip("# ").strip()
    req = urllib.request.Request(
        "https://api.github.com/repos/{0}/issues".format(repo),
        data=json.dumps({"title": title, "body": md, "labels": ["daily-report"]}).encode(),
        method="POST",
        headers={"Authorization": "Bearer " + token, "Accept": "application/vnd.github+json",
                 "User-Agent": "pickixo-shorts"})
    try:
        with urllib.request.urlopen(req, timeout=30):
            pass
    except Exception as e:
        common.log("could not open report issue: {0}".format(e))
