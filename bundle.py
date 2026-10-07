#!/usr/bin/env python3
"""Package tonight's build into /workspace/tokenmax/TokenMax-Oct7-build.zip.

Contents (read-only on every project folder; nothing outside hub/ is modified except the zip itself):
  TokenMax-Oct7-build/index.html            offline hub (data embedded, links relative)
  TokenMax-Oct7-build/style.css, app.js
  TokenMax-Oct7-build/projects/<name>/...   README.md, offline snapshot HTML(s) <= 15 MB, dist/*.pdf < 10 MB,
                                            best screenshots (00-best-* + up to two others, desktop preferred)
  TokenMax-Oct7-build/build-night-recap.pdf, build-night-poster.png
  Private projects (PRIVATE) get README.md + PICTURE-WITHHELD.md only.
  TokenMax-Oct7-build/hub/...               hub README + hub screenshots
  TokenMax-Oct7-build/MANIFEST.md           every file with size, plus anything skipped and why
Only trailer/out/build-night-trailer-720p.mp4 is bundled (if it fits); every other video is skipped and listed in MANIFEST.md.
A staging copy is left at hub/dist/bundle-preview/ so the offline index can be screenshotted.
"""
import datetime as dt, glob, json, re, zlib, os, shutil, sys, zipfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scan

HUB = os.path.dirname(os.path.abspath(__file__))
OUT_ZIP = os.path.join(scan.ROOT, "TokenMax-Oct7-build.zip")
TOP = "TokenMax-Oct7-build"
STAGE = os.path.join(HUB, "dist", "bundle-preview")
CAP = 100 * 1024 * 1024          # hard limit from the brief
BUDGET = 95 * 1000 * 1000        # zip must end up under 95 MB (decimal)
IMG = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
SNAP_MAX = 15 * 1000 * 1000      # skip any single snapshot HTML over 15 MB
PDF_MAX = 10 * 1000 * 1000       # bundle dist/*.pdf under 10 MB
TRAILER = os.path.join(scan.ROOT, "trailer", "out", "build-night-trailer-720p.mp4")
RECAP = [os.path.join(scan.ROOT, "recap", "dist", f) for f in ("build-night-recap.pdf", "build-night-poster.png")]
# private projects: README + a "picture withheld" note only
PRIVATE = {"kpd-build-kits": "build plans based on the internal KPD code map.",
    "kpd-code-atlas": "internal map of the KPD codebase (its PDF brief and snapshot are internal too).",
    "docket-pilot": "built on work data.",
    "slack-pulse": "built on work Slack data.",
    "ai-ops-atlas": "built on work data.",
    "trip-kit": "its screenshots show flight confirmation codes.",
    "kpd-ai-deck": "internal work deck.",
}


def main():
    data = scan.hub_data(do_ping=True)
    data["bundledAt"] = data["generatedAt"]
    files, skipped, notes = [], [], []  # files: (src, arcname-under-TOP); notes: (arcname, text)

    for p in data["projects"]:
        name = p["name"]
        base = os.path.join(scan.ROOT, name)
        arcbase = f"projects/{name}"
        if p["hasReadme"]:
            files.append((os.path.join(base, "README.md"), f"{arcbase}/README.md"))
        p["videos"] = []          # project videos are not bundled (only the trailer 720p, added below)
        p["withheld"] = name in PRIVATE
        if name in PRIVATE:
            # README + withheld note only: no screenshots, no snapshot (snapshots embed images), no PDFs
            notes.append((f"{arcbase}/PICTURE-WITHHELD.md",
                          f"# Picture withheld\n\n{p['title']} (`{name}/`) is private: {PRIVATE[name]}\n"
                          "Its screenshots and snapshot images were left out of this bundle on purpose. "
                          "See README.md for what it does; the full project lives on the box.\n"))
            for rel in p["snapshots"]:
                skipped.append((f"{arcbase}/{rel}", "private project: snapshot withheld (contains internal pictures/data)"))
            for f in sorted(glob.glob(os.path.join(base, "dist", "*.pdf"))):
                skipped.append((f"{arcbase}/{os.path.relpath(f, base)}", "private project: PDF withheld"))
            if p["screenshots"]:
                skipped.append((f"{arcbase}/screenshots/ ({len(p['screenshots'])} files)", "private project: picture withheld"))
            p["snapshots"], p["snapshotBytes"], p["cover"] = [], 0, None
            continue
        if not p["snapshots"]:   # offline single-file builds not named *snapshot*.html (e.g. dist/<name>.html)
            htmls = sorted(os.path.relpath(f, base) for f in glob.glob(os.path.join(base, "dist", "*.html")))
            p["snapshots"] = [h for h in htmls if os.path.basename(h) != "index.html"] or htmls
        p["ready"] = bool(p["hasReadme"] and p["snapshots"])   # an oversized snapshot still counts as built
        keep_snaps = []
        for rel in p["snapshots"]:
            sz = os.path.getsize(os.path.join(base, rel))
            if sz > SNAP_MAX:
                skipped.append((f"{arcbase}/{rel}", f"snapshot HTML is {sz/1e6:.1f} MB (> 15 MB); open it on the box"))
            else:
                keep_snaps.append(rel); files.append((os.path.join(base, rel), f"{arcbase}/{rel}"))
        p["snapshots"] = keep_snaps
        p["snapshotBytes"] = sum(os.path.getsize(os.path.join(base, r)) for r in keep_snaps)
        for f in sorted(glob.glob(os.path.join(base, "dist", "*.pdf"))):
            rel, sz = os.path.relpath(f, base), os.path.getsize(f)
            if sz < PDF_MAX:
                files.append((f, f"{arcbase}/{rel}"))
            else:
                skipped.append((f"{arcbase}/{rel}", f"PDF is {sz/1e6:.1f} MB (>= 10 MB)"))
        imgs = [r for r in p["screenshots"] if os.path.splitext(r)[1].lower() in IMG]
        best = [r for r in imgs if os.path.basename(r).startswith("00-best")]
        rest = sorted((r for r in imgs if r not in best), key=lambda r: ("desktop" not in os.path.basename(r).lower(), r))
        chosen = best + rest[:2]
        for rel in chosen:
            files.append((os.path.join(base, rel), f"{arcbase}/{rel}"))
        if len(p["screenshots"]) > len(chosen):
            skipped.append((f"{arcbase}/screenshots/ ({len(p['screenshots']) - len(chosen)} of {len(p['screenshots'])} files)",
                            "only the best screenshots are bundled (00-best-* plus up to two others)"))
        if p["cover"] not in chosen:
            p["cover"] = best[0] if best else scan.pick_shot(chosen)
        p["bundledScreenshots"] = chosen
        if not p["ready"]:
            miss = [m for m, ok in (("README.md", p["hasReadme"]), ("dist/*.html snapshot", bool(p["snapshots"]))) if not ok]
            skipped.append((arcbase, f"no offline snapshot HTML / README at bundle time (whatever exists is included): missing {', '.join(miss)}"))

    # project videos: list every one (except the bundled trailer 720p) as skipped
    for p in scan.projects(do_ping=False):
        for rel in p["videos"] + [r for r in p["screenshots"] if os.path.splitext(r)[1].lower() in scan.VIDEO_EXT]:
            full = os.path.join(scan.ROOT, p["name"], rel)
            if os.path.abspath(full) != TRAILER and os.path.exists(full):
                skipped.append((f"projects/{p['name']}/{rel}", f"video not bundled ({os.path.getsize(full)/1e6:.1f} MB); only the trailer 720p MP4 is included"))
    for f in sorted(glob.glob(os.path.join(os.path.dirname(TRAILER), "*.gif"))):
        skipped.append((f"projects/trailer/{os.path.relpath(f, os.path.join(scan.ROOT, 'trailer'))}", f"trailer GIF not bundled ({os.path.getsize(f)/1e6:.1f} MB)"))

    # recap PDF + poster at the bundle's top level
    for f in RECAP:
        if os.path.exists(f):
            files.append((f, os.path.basename(f)))
        else:
            skipped.append((os.path.basename(f), "not found at bundle time"))

    # hub's own docs + screenshots (01-projects is the live hub, whose covers show private projects: left out)
    if os.path.exists(os.path.join(HUB, "README.md")):
        files.append((os.path.join(HUB, "README.md"), "hub/README.md"))
    shots_dir = os.path.join(HUB, "screenshots")
    for f in sorted(os.listdir(shots_dir)) if os.path.isdir(shots_dir) else []:
        if os.path.splitext(f)[1].lower() in IMG:
            if f.startswith("01-projects"):
                skipped.append((f"hub/screenshots/{f}", "live-hub screenshot shows private projects' covers"))
                continue
            files.append((os.path.join(shots_dir, f), f"hub/screenshots/{f}"))

    def zsize(path):  # estimated bytes inside the zip (images/videos are stored, everything else deflated)
        if path.lower().endswith((".mp4", ".png", ".jpg", ".jpeg", ".gif", ".webp")):
            return os.path.getsize(path)
        return len(zlib.compress(open(path, "rb").read(), 6))
    used = sum(zsize(s) + 200 for s, _ in files) + 2_000_000   # + headers, index.html, MANIFEST.md
    tarc = "projects/trailer/" + os.path.relpath(TRAILER, os.path.join(scan.ROOT, "trailer"))
    if os.path.exists(TRAILER):
        tsz = os.path.getsize(TRAILER)
        if used + tsz <= BUDGET:
            files.append((TRAILER, tarc)); used += tsz
            for p in data["projects"]:
                if p["name"] == "trailer":
                    p["videos"] = [os.path.relpath(TRAILER, os.path.join(scan.ROOT, "trailer"))]
        else:
            skipped.append((tarc, f"trailer skipped to keep the zip under 95 MB ({tsz/1e6:.1f} MB)"))

    # ---- stage ----
    shutil.rmtree(STAGE, ignore_errors=True)
    root = os.path.join(STAGE, TOP)
    os.makedirs(root)
    for src, arc in files:
        dst = os.path.join(root, arc)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
    # snapshots that embed other projects' pictures (e.g. the museum's placards): drop private projects' images
    priv_img = re.compile(r'("name": ?"(?:' + "|".join(map(re.escape, PRIVATE)) + r')"(?:[^{}]|\{[^{}]*\})*?"image": ?)\{[^{}]*\}')
    for src, arc in files:
        if arc.endswith(".html"):
            dst = os.path.join(root, arc)
            txt = open(dst, encoding="utf-8", errors="surrogateescape").read()
            new_txt, n = priv_img.subn(r"\1null", txt)
            if n:
                open(dst, "w", encoding="utf-8", errors="surrogateescape").write(new_txt)
                skipped.append((arc, f"kept, but {n} embedded private-project picture(s) removed from the staged copy"))
    web = os.path.join(HUB, "web")
    shutil.copy2(os.path.join(web, "style.css"), root)
    js = open(os.path.join(web, "app.js")).read()
    js = js.replace('"<span>no screenshot yet</span>"', '(p.withheld ? "<span>picture withheld (private)</span>" : "<span>no screenshot yet</span>")')
    open(os.path.join(root, "app.js"), "w").write(js)
    for arc, text in notes:
        dst = os.path.join(root, arc)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        open(dst, "w").write(text)
    html = open(os.path.join(web, "index.html")).read()
    blob = json.dumps(data).replace("</", "<\\/")
    html = html.replace('<script src="app.js"></script>', f'<script>window.HUB_SNAPSHOT={blob};</script>\n<script src="app.js"></script>')
    open(os.path.join(root, "index.html"), "w").write(html)

    now = dt.datetime.now(scan.ET)
    lines = [f"# TokenMax Oct 7 build bundle", "", f"Bundled {now.strftime('%a %b %-d %Y, %-I:%M %p')} ET by hub/bundle.py. Open `index.html` in a browser; everything links relatively. `build-night-recap.pdf` and `build-night-poster.png` sit next to it.", "",
             "## Projects", ""]
    for p in data["projects"]:
        lines.append(f"- **{p['title']}** (`{p['name']}/`): {'ready' if p['ready'] else 'still building'}; port {p['port'] or 'none'}; "
                     f"{p['counts']['files']} files, {p['counts']['loc']} LOC, {p['counts']['screenshots']} screenshots, {p['counts']['tests']} tests (measured).")
    lines += ["", "## Skipped", ""] + ([f"- `{a}`: {why}" for a, why in skipped] or ["- nothing"])
    lines += ["", "## Files", "", "| path | bytes |", "|---|---:|"]
    all_files = []
    for d, _, fs in os.walk(root):
        for f in fs:
            full = os.path.join(d, f)
            all_files.append((os.path.relpath(full, root), os.path.getsize(full)))
    all_files.sort()
    lines += [f"| {a} | {b:,} |" for a, b in all_files]
    open(os.path.join(root, "MANIFEST.md"), "w").write("\n".join(lines) + "\n")

    # ---- zip (write to temp then atomically replace) ----
    tmp = OUT_ZIP + ".tmp"
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for d, _, fs in os.walk(root):
            for f in sorted(fs):
                full = os.path.join(d, f)
                arc = os.path.join(TOP, os.path.relpath(full, root))
                ct = zipfile.ZIP_STORED if f.lower().endswith((".mp4", ".png", ".jpg", ".jpeg", ".gif", ".webp")) else zipfile.ZIP_DEFLATED
                z.write(full, arc, compress_type=ct)
    size = os.path.getsize(tmp)
    if size >= BUDGET:
        os.remove(tmp)
        sys.exit(f"bundle would be {size/1e6:.1f} MB (>= 95 MB); aborting")
    os.replace(tmp, OUT_ZIP)
    print(f"wrote {OUT_ZIP}: {size:,} bytes ({size/1024/1024:.1f} MiB), {len(all_files)} files")
    for a, why in skipped:
        print(f"  skipped {a}: {why}")


if __name__ == "__main__":
    main()
