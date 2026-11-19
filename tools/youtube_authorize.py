"""One-time YouTube authorization for one channel. Run on your Mac:

    python3 tools/youtube_authorize.py ch01

1. Opens your browser -> pick the YouTube channel for ch01 -> Allow.
2. Shows which channel was authorized.
3. Saves the refresh token straight into GitHub Secrets as YT_REFRESH_CH01
   (via the `gh` CLI; the token is never printed) and enables ch01 in config.

Needs the OAuth client from Google Cloud (Desktop app). The first run asks for its
client id/secret and stores them as GitHub secrets YT_CLIENT_ID / YT_CLIENT_SECRET.
Only Python's standard library is used."""

import getpass
import http.server
import json
import os
import secrets as pysecrets
import subprocess
import sys
import threading
import urllib.parse
import urllib.request
import webbrowser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHANNELS = os.path.join(ROOT, "config", "channels.json")
SCOPES = "https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube.readonly"
KEYCHAIN_SERVICE = "pickixo-youtube-oauth"


def keychain_get(account):
    p = subprocess.run(["security", "find-generic-password", "-s", KEYCHAIN_SERVICE,
                        "-a", account, "-w"], capture_output=True, text=True)
    return p.stdout.strip() if p.returncode == 0 else ""


def keychain_set(account, value):
    subprocess.run(["security", "add-generic-password", "-U", "-s", KEYCHAIN_SERVICE,
                    "-a", account, "-w", value], check=True, capture_output=True)


def gh_bin():
    import shutil
    for c in [shutil.which("gh"), os.path.expanduser("~/.local/bin/gh"),
              "/opt/homebrew/bin/gh", "/usr/local/bin/gh"]:
        if c and os.path.exists(c):
            return c
    sys.exit("GitHub CLI (gh) not found. Install it or add it to PATH.")


def gh_secret(name, value):
    p = subprocess.run([gh_bin(), "secret", "set", name], input=value, text=True,
                       capture_output=True, cwd=ROOT)
    if p.returncode != 0:
        sys.exit("Could not save {0} to GitHub: {1}".format(name, p.stderr.strip()[:300]))


def client_creds():
    cid, csec = keychain_get("client_id"), keychain_get("client_secret")
    if cid and csec:
        return cid, csec
    print("Paste the OAuth client from Google Cloud (Desktop app).")
    cid = input("Client ID: ").strip()
    csec = getpass.getpass("Client secret (hidden): ").strip()
    keychain_set("client_id", cid)
    keychain_set("client_secret", csec)
    gh_secret("YT_CLIENT_ID", cid)
    gh_secret("YT_CLIENT_SECRET", csec)
    print("Saved client id/secret to Keychain and GitHub secrets.")
    return cid, csec


def wait_for_code(port, state):
    result = {}

    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            if q.get("state", [""])[0] == state and "code" in q:
                result["code"] = q["code"][0]
                msg = "Done. You can close this tab and go back to the terminal."
            else:
                result["error"] = q.get("error", ["unknown"])[0]
                msg = "Authorization failed: " + result["error"]
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(msg.encode())

        def log_message(self, *a):
            pass

    srv = http.server.HTTPServer(("127.0.0.1", port), H)
    t = threading.Thread(target=srv.handle_request)
    t.start()
    return srv, t, result


def main():
    if len(sys.argv) != 2:
        sys.exit("usage: python3 tools/youtube_authorize.py ch01   (or --client to only save the OAuth client)")
    if sys.argv[1] == "--client":
        client_creds()
        print("OAuth client saved. Authorize channels after the app is published (In production).")
        return
    ch_id = sys.argv[1].lower()
    cfg = json.load(open(CHANNELS))
    ch = next((c for c in cfg["channels"] if c["id"] == ch_id), None)
    if not ch:
        sys.exit("unknown channel id " + ch_id)

    cid, csec = client_creds()
    port, state = 8765, pysecrets.token_urlsafe(16)
    redirect = "http://127.0.0.1:{0}".format(port)
    srv, t, result = wait_for_code(port, state)
    url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode({
        "client_id": cid, "redirect_uri": redirect, "response_type": "code", "scope": SCOPES,
        "access_type": "offline", "prompt": "consent select_account", "state": state})
    print("\nOpening the browser. Choose the channel for {0} ({1}) and click Allow.".format(
        ch_id, ch["niche"]))
    webbrowser.open(url)
    t.join(timeout=300)
    srv.server_close()
    if "code" not in result:
        sys.exit("No authorization received: " + result.get("error", "timeout"))

    body = urllib.parse.urlencode({"code": result["code"], "client_id": cid, "client_secret": csec,
                                   "redirect_uri": redirect, "grant_type": "authorization_code"}).encode()
    tok = json.loads(urllib.request.urlopen(
        urllib.request.Request("https://oauth2.googleapis.com/token", data=body), timeout=30).read())
    if "refresh_token" not in tok:
        sys.exit("Google returned no refresh token. Remove the app's access at "
                 "myaccount.google.com/permissions and run this again.")

    req = urllib.request.Request(
        "https://www.googleapis.com/youtube/v3/channels?part=snippet&mine=true",
        headers={"Authorization": "Bearer " + tok["access_token"]})
    items = json.loads(urllib.request.urlopen(req, timeout=30).read()).get("items", [])
    if not items:
        sys.exit("That Google account has no YouTube channel selected. Try again and pick a channel.")
    sn = items[0]["snippet"]
    title, handle = sn.get("title", ""), sn.get("customUrl", "")
    print("Authorized channel: {0} {1}".format(title, handle))

    gh_secret("YT_REFRESH_" + ch_id.upper(), tok["refresh_token"])
    ch.update(name=title, handle=handle, enabled=True)
    with open(CHANNELS, "w") as f:
        json.dump(cfg, f, indent=2)
        f.write("\n")
    print("Saved YT_REFRESH_{0} to GitHub and enabled {1} in config/channels.json.".format(
        ch_id.upper(), ch_id))
    print("Commit and push config/channels.json so the daily run picks it up.")


if __name__ == "__main__":
    main()
