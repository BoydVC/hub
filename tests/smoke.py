#!/usr/bin/env python3
"""TokenMax Hub smoke test: API, deeplinks vs profile folders, rendered DOM per tab, and the zip bundle."""
import glob, json, os, re, shutil, subprocess, sys, tempfile, urllib.error, urllib.request, zipfile

HUB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = f"http://127.0.0.1:{os.environ.get('HUB_PORT', '4646')}"
ZIP = "/workspace/tokenmax/TokenMax-Oct7-build.zip"
AGENT_IDS = {os.path.basename(os.path.dirname(p)) for p in glob.glob("/home/box/agent-data/agents/*/profile.json")}
CHROME = shutil.which("google-chrome") or shutil.which("chromium")
fails, passes = [], 0


def check(cond, msg):
    global passes
    if cond:
        passes += 1; print("  ok  ", msg)
    else:
        fails.append(msg); print("  FAIL", msg)


def get(path):
    try:
        with urllib.request.urlopen(BASE + path, timeout=20) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, b""


def dom(url):
    prof = tempfile.mkdtemp(prefix="hubsmoke")
    try:
        return subprocess.run([CHROME, "--headless=new", "--no-sandbox", "--disable-gpu", "--window-size=1440,900",
                               "--virtual-time-budget=5000", f"--user-data-dir={prof}", "--dump-dom", url],
                              capture_output=True, text=True, timeout=90).stdout
    finally:
        shutil.rmtree(prof, ignore_errors=True)


print("API")
st, body = get("/api/health")
check(st == 200 and json.loads(body).get("ok"), "/api/health ok")
st, body = get("/api/hub")
d = json.loads(body)
check(st == 200, "/api/hub 200")
names = [p["name"] for p in d["projects"]]
check(len(names) >= 4, f"≥4 projects detected ({names})")
check("hub" not in names, "hub excludes itself from project cards")
check(all(os.path.isdir(f"/workspace/tokenmax/{n}") for n in names), "every card is a real folder")
for p in d["projects"]:
    if p["ready"]:
        s, _ = get(f"/p/{p['name']}/{p['snapshots'][0]}")
        check(s == 200, f"{p['name']} snapshot served")
    if p["cover"]:
        s, _ = get(f"/p/{p['name']}/{p['cover']}")
        check(s == 200, f"{p['name']} cover served")
check(get("/p/../../etc/passwd")[0] == 404 and get("/p/bot-island/../../../etc/passwd")[0] == 404, "path traversal blocked")
check(get("/p/bot-island/data/fleet.json")[0] == 404, "non-media files not exposed via /p/")

print("Bot Launcher")
ids = {b["id"] for b in d["bots"]}
check(ids == AGENT_IDS, f"one card per profile folder ({len(ids)} bots)")
check(all(b["deeplink"] == f"grokbot://app/v1/agent?id={b['id']}" for b in d["bots"]), "deeplinks use exact grokbot://app/v1/agent?id=<folder id>")
check(all(re.fullmatch(r"#[0-9a-f]{6}", b["color"]) for b in d["bots"]), "every bot has an avatar color")

print("Story")
s = d["story"]
check(s["usage"] and "used_pct" in s["usage"], "usage.json loaded")
check(s["totals"]["loc"] > 0 and len(s["lanes"]) >= 4, f"timeline lanes={len(s['lanes'])} loc={s['totals']['loc']}")

print("Rendered DOM (headless Chrome)")
if CHROME:
    h = dom(BASE + "/?tab=projects")
    check(h.count('class="pcard"') == len(names), f"projects tab renders {len(names)} cards")
    h = dom(BASE + "/?tab=story")
    check('class="timeline"' in h and "Per project" in h, "story tab renders timeline + table")
    h = dom(BASE + "/?tab=bots")
    links = re.findall(r'href="(grokbot:[^"]*)"', h)
    check(len(links) == len(AGENT_IDS), f"bots tab renders {len(links)} deeplinks")
    check(all(re.fullmatch(r"grokbot://app/v1/agent\?id=([0-9a-f-]{36})", l) and l.split("=")[1] in AGENT_IDS for l in links), "every rendered deeplink matches a profile id")
    check(not re.search(r"grokbot://(?!app/v1/agent\?id=)", h), "no other grokbot:// formats")
else:
    print("  skip  no chrome")

print("Bundle")
check(os.path.exists(ZIP), "zip exists")
if os.path.exists(ZIP):
    size = os.path.getsize(ZIP)
    check(size < 100 * 1024 * 1024, f"zip under 100 MB ({size/1e6:.1f} MB)")
    z = zipfile.ZipFile(ZIP)
    zn = set(z.namelist())
    idx = "TokenMax-Oct7-build/index.html"
    check(idx in zn, "zip has index.html")
    check(z.testzip() is None, "zip CRCs valid")
    html = z.read(idx).decode()
    m = re.search(r"window\.HUB_SNAPSHOT=(\{.*?\});</script>", html, re.S)
    check(bool(m), "index.html embeds HUB_SNAPSHOT")
    if m:
        snap = json.loads(m.group(1).replace("<\\/", "</"))
        missing = []
        for p in snap["projects"]:
            for rel in p["snapshots"] + ([p["cover"]] if p["cover"] else []) + p["videos"] + (["README.md"] if p["hasReadme"] else []):
                if f"TokenMax-Oct7-build/projects/{p['name']}/{rel}" not in zn:
                    missing.append(f"{p['name']}/{rel}")
        check(not missing, f"every offline link resolves inside the zip {missing[:5]}")
    check("TokenMax-Oct7-build/MANIFEST.md" in zn, "zip has MANIFEST.md")
    preview = os.path.join(HUB, "dist/bundle-preview/TokenMax-Oct7-build/index.html")
    if CHROME and os.path.exists(preview):
        h = dom("file://" + preview + "?tab=bots")
        check(h.count("grokbot://app/v1/agent?id=") >= len(AGENT_IDS), "offline index renders bot launcher from file://")

print(f"\n{passes} passed, {len(fails)} failed")
sys.exit(1 if fails else 0)
