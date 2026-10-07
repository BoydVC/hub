#!/usr/bin/env python3
"""TokenMax Hub scanner: everything the hub shows, computed from the filesystem (read-only).

- projects(): every folder in /workspace/tokenmax; "ready" = has README.md AND dist/*snapshot*.html
- story():    build-session timeline from file mtimes + per-project counts (files, LOC, screenshots, tests)
- bots():     Grok Bots from /home/box/agent-data/agents/*/profile.json + schedules from Bot Island's fleet.json
Nothing here writes outside the hub folder.
"""
import datetime as dt
import glob
import json
import os
import re
import socket
import sys
import urllib.error
import urllib.request
from zoneinfo import ZoneInfo

ROOT = os.environ.get("TOKENMAX_ROOT", "/workspace/tokenmax")
AGENTS = os.environ.get("AGENTS_DIR", "/home/box/agent-data/agents")
FLEET = os.path.join(ROOT, "bot-island", "data", "fleet.json")
ET = ZoneInfo("America/New_York")
HUB = os.path.basename(os.path.dirname(os.path.abspath(__file__)))  # "hub"

SKIP_DIRS = {"vendor", "vendor_tts", "__pycache__", "node_modules", ".git", ".venv", "venv", "site-packages"}
CODE_EXT = {".py", ".js", ".mjs", ".ts", ".html", ".css", ".sh"}
NON_CODE_DIRS = {"dist", "data", "out", "screenshots", "assets", "tts", "reports"}
SHOT_EXT = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".mp4"}
VIDEO_EXT = {".mp4", ".webm", ".mov"}
COLORS = {"blue": "#3b82f6", "red": "#ef4444", "green": "#22c55e", "yellow": "#eab308", "gray": "#94a3b8", "orange": "#f97316",
          "cyan": "#06b6d4", "violet": "#8b5cf6", "magenta": "#d946ef", "purple": "#8b5cf6", "pink": "#ec4899", "teal": "#14b8a6"}
SESSION_START = dt.datetime(2026, 10, 7, 15, 0, tzinfo=ET)  # window for the timeline (session began ~3:20 PM ET)


def walk(proj_dir):
    """Yield (relpath, abspath, stat) for every file, skipping vendored/cache dirs."""
    for base, dirs, files in os.walk(proj_dir):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.endswith(".dist-info")]
        for f in files:
            p = os.path.join(base, f)
            try:
                st = os.stat(p)
            except OSError:
                continue
            yield os.path.relpath(p, proj_dir), p, st


def readme_info(path):
    """Title (H1) and a one-line pitch: the first bold sentence of the first paragraph, else its first sentence."""
    if not os.path.exists(path):
        return None, None
    lines = open(path, encoding="utf-8", errors="replace").read().splitlines()
    title = next((l[2:].strip() for l in lines if l.startswith("# ")), None)
    para = []
    started = False
    for l in lines:
        if l.startswith("#") or l.startswith("!") or l.startswith("|"):
            if started:
                break
            continue
        if not l.strip():
            if started:
                break
            continue
        started = True
        para.append(l.strip())
    text = " ".join(para)
    m = re.match(r"\*\*(.+?)\*\*", text)
    pitch = m.group(1) if m else re.split(r"(?<=[.!?])\s", re.sub(r"[*_`]", "", text))[0]
    return title, pitch.strip()


def detect_port(proj_dir):
    cfg = os.path.join(proj_dir, "config.json")
    try:
        p = json.load(open(cfg)).get("port")
        if p:
            return int(p)
    except Exception:
        pass
    for name in ("README.md", "run.sh", "server.py"):
        f = os.path.join(proj_dir, name)
        if os.path.exists(f):
            s = open(f, encoding="utf-8", errors="replace").read()
            m = re.search(r"127\.0\.0\.1:(\d{4,5})", s) or re.search(r"PORT[^\n]*?(\d{4,5})", s)
            if m:
                return int(m.group(1))
    return None


def ping(port, timeout=1.2):
    """Is something answering on 127.0.0.1:port? Tries /api/health, then /, then a bare TCP connect."""
    if not port:
        return {"live": False, "why": "no port found"}
    why = "refused"
    for path in ("/api/health", "/"):
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=timeout) as r:
                return {"live": True, "path": path, "code": r.status}
        except urllib.error.HTTPError as e:
            if e.code < 500 and e.code != 404:
                return {"live": True, "path": path, "code": e.code}
            why = f"HTTP {e.code}"
        except Exception as e:  # noqa: BLE001
            why = type(e).__name__
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=timeout):
            return {"live": True, "path": "tcp"}
    except OSError:
        return {"live": False, "why": why}


SHOT_PREF = ["01-", "live", "wall", "overview", "hero", "studio", "launch"]


def pick_shot(shots):
    imgs = [s for s in shots if os.path.splitext(s)[1].lower() in {".png", ".jpg", ".jpeg", ".webp"}]
    for pref in SHOT_PREF:
        for s in sorted(imgs):
            if os.path.basename(s).lower().startswith(pref):
                return s
    return sorted(imgs)[0] if imgs else None


def project(name, do_ping=True):
    d = os.path.join(ROOT, name)
    files = list(walk(d))
    title, pitch = readme_info(os.path.join(d, "README.md"))
    snaps = sorted(glob.glob(os.path.join(d, "dist", "*snapshot*.html")))
    shots = sorted(r for r, p, st in files if r.split(os.sep)[0] == "screenshots" and os.path.splitext(r)[1].lower() in SHOT_EXT)
    # finished videos only: skip hidden/work/tmp dirs (render scratch) and stub files under 50 KB
    videos = sorted(r for r, p, st in files if os.path.splitext(r)[1].lower() in VIDEO_EXT and st.st_size >= 50_000
                    and not any(seg.startswith((".", "work", "tmp", "_")) for seg in r.split(os.sep)[:-1]))
    # hand-written code only: skip build bundles / minified files (> 200 KB, e.g. a game.js with three.js inlined)
    code = [(r, p) for r, p, st in files if os.path.splitext(r)[1].lower() in CODE_EXT and r.split(os.sep)[0] not in NON_CODE_DIRS and st.st_size <= 200_000]
    loc = 0
    for r, p in code:
        try:
            loc += sum(1 for _ in open(p, encoding="utf-8", errors="replace"))
        except OSError:
            pass
    tests = sorted(r for r, p, st in files if r.split(os.sep)[0] == "tests" or re.search(r"(^|/)(test_|smoke)", r))
    mt = [st.st_mtime for r, p, st in files]
    port = detect_port(d)
    return {
        "name": name, "title": title or name, "pitch": pitch,
        "ready": bool(os.path.exists(os.path.join(d, "README.md")) and snaps),
        "hasReadme": os.path.exists(os.path.join(d, "README.md")),
        "snapshots": [os.path.relpath(s, d) for s in snaps],
        "snapshotBytes": sum(os.path.getsize(s) for s in snaps),
        "port": port, "status": ping(port) if do_ping else None,
        "screenshots": shots, "cover": pick_shot(shots), "videos": videos,
        "counts": {"files": len(files), "codeFiles": len(code), "loc": loc, "screenshots": len(shots), "tests": len(tests),
                   "bytes": sum(st.st_size for r, p, st in files)},
        "tests": tests,
        "firstMtime": dt.datetime.fromtimestamp(min(mt), ET).isoformat(timespec="seconds") if mt else None,
        "lastMtime": dt.datetime.fromtimestamp(max(mt), ET).isoformat(timespec="seconds") if mt else None,
    }


def projects(do_ping=True, include_hub=False):
    out = []
    for name in sorted(os.listdir(ROOT)):
        d = os.path.join(ROOT, name)
        if not os.path.isdir(d) or name.startswith(".") or (name == HUB and not include_hub):
            continue
        out.append(project(name, do_ping))
    out.sort(key=lambda p: (not p["ready"], p["firstMtime"] or ""))
    return out


def story(projs=None):
    projs = projs or projects(do_ping=False, include_hub=True)
    now = dt.datetime.now(ET)
    end = max(now, SESSION_START + dt.timedelta(hours=4))
    bucket = 5 * 60
    lanes, milestones = [], []
    for p in projs:
        d = os.path.join(ROOT, p["name"])
        hist = {}
        for r, path, st in walk(d):
            t = dt.datetime.fromtimestamp(st.st_mtime, ET)
            if t < SESSION_START:
                continue
            k = int((t - SESSION_START).total_seconds() // bucket)
            hist[k] = hist.get(k, 0) + 1
            base = os.path.basename(r)
            if r == "README.md":
                milestones.append({"project": p["name"], "at": t.isoformat(timespec="seconds"), "what": "README written (last edit)"})
            elif r.startswith("dist" + os.sep) and "snapshot" in base:
                milestones.append({"project": p["name"], "at": t.isoformat(timespec="seconds"), "what": "offline snapshot exported (last)"})
        shots = [os.path.getmtime(os.path.join(d, s)) for s in p["screenshots"]]
        if shots:
            milestones.append({"project": p["name"], "at": dt.datetime.fromtimestamp(min(shots), ET).isoformat(timespec="seconds"), "what": f"earliest surviving screenshot ({len(shots)} total)"})
        lanes.append({"project": p["name"], "buckets": hist, "first": p["firstMtime"], "last": p["lastMtime"], "counts": p["counts"]})
    for f in ("SHORTLIST.md", "usage.json"):
        fp = os.path.join(ROOT, f)
        if os.path.exists(fp):
            milestones.append({"project": "tokenmax", "at": dt.datetime.fromtimestamp(os.path.getmtime(fp), ET).isoformat(timespec="seconds"), "what": f"{f} last updated"})
    milestones.sort(key=lambda m: m["at"])
    usage = None
    try:
        usage = json.load(open(os.path.join(ROOT, "usage.json")))
    except Exception:
        pass
    tot = {k: sum(l["counts"][k] for l in lanes) for k in ("files", "loc", "screenshots", "tests", "codeFiles")}
    return {"start": SESSION_START.isoformat(), "end": end.isoformat(timespec="seconds"), "now": now.isoformat(timespec="seconds"),
            "bucketMinutes": bucket // 60, "lanes": lanes, "milestones": milestones, "usage": usage, "totals": tot,
            "note": "Times are file last-modified times (mtime). A file edited many times only shows its latest edit, so early work is under-represented."}


def cron_english(cron):
    m, h, dom, mon, dow = cron.split()
    try:
        hours = [int(x) for x in h.split(",")]
        times = " & ".join(dt.time(hh, int(m)).strftime("%-I:%M %p") for hh in hours)
    except ValueError:
        times = f"{h}:{m}"
    days = {"*": "daily", "1-5": "weekdays", "1": "Mondays", "0": "Sundays", "6": "Saturdays", "0,6": "weekends"}.get(dow, f"days {dow}")
    return f"{times} {days}"


def bots():
    fleet = {}
    try:
        fleet = {b["id"]: b for b in json.load(open(FLEET))["bots"]}
    except Exception:
        pass
    out = []
    for prof in sorted(glob.glob(os.path.join(AGENTS, "*", "profile.json"))):
        aid = os.path.basename(os.path.dirname(prof))
        try:
            p = json.load(open(prof))
        except Exception:
            continue
        desc = (p.get("description") or "").strip()
        first = re.split(r"(?<=[.!?])\s", re.sub(r"\s+", " ", desc))[0] if desc else ""
        role = (p.get("title") or "").strip()
        # display form of the description's first sentence: drop the prompt-style "You are " prefix only
        if first.startswith("You are "):
            first = first[8:9].upper() + first[9:]
        fb = fleet.get(aid, {})
        sched = [f"{r['name']}: {cron_english(r['cron'])}" for r in fb.get("routines", []) if r.get("enabled")]
        paused = [r["name"] for r in fb.get("routines", []) if not r.get("enabled")]
        rhythm = [f"observed output ~{dt.time(o['hour'], o['minute']).strftime('%-I:%M %p')} ({o['days']} days)" for o in fb.get("observedRhythm", [])]
        color = p.get("avatarColor") or fb.get("color") or ""
        out.append({
            "id": aid, "name": p.get("name") or "(unnamed)", "role": role, "roleFrom": "title" if role else ("description" if first else "none"),
            "oneLiner": first[:180] + ("…" if len(first) > 180 else ""),
            "color": COLORS.get(color, "#94a3b8"), "colorName": color or "unset", "shape": p.get("avatarShape") or fb.get("shape") or "circle",
            "schedule": sched, "paused": paused, "rhythm": rhythm, "inBotIsland": bool(fb),
            "deeplink": f"grokbot://app/v1/agent?id={aid}",
        })
    out.sort(key=lambda b: (b["name"] == "New Bot", b["name"].lower()))
    return {"bots": out, "fleetGeneratedAt": json.load(open(FLEET)).get("generatedAt") if os.path.exists(FLEET) else None}


def hub_data(do_ping=True):
    ps = projects(do_ping)
    return {"generatedAt": dt.datetime.now(ET).isoformat(timespec="seconds"), "projects": ps,
            "story": story(projects(do_ping=False, include_hub=True)), **bots()}


if __name__ == "__main__":
    d = hub_data()
    for p in d["projects"]:
        print(f"{p['name']:18} ready={p['ready']!s:5} port={p['port']} live={p['status']['live']} cover={p['cover']} counts={p['counts']}")
    print("totals", d["story"]["totals"], "milestones", len(d["story"]["milestones"]))
    for b in d["bots"]:
        print(f"  {b['name']:28} {b['role'] or '['+b['roleFrom']+']':20} {b['colorName']:8} {b['schedule'][:2]} {b['rhythm']}")
    sys.exit(0)
