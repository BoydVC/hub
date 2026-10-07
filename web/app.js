/* TokenMax Hub. Live mode: GET /api/hub. Offline mode (bundle index.html): window.HUB_SNAPSHOT, assets via relative paths. */
"use strict";
let D;
const OFF = !!window.HUB_SNAPSHOT;
const S = { tab: new URLSearchParams(location.search).get("tab") || (location.hash || "#projects").slice(1) };
const $ = (q) => document.querySelector(q);
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const fmt = (n) => (n == null ? "—" : Number(n).toLocaleString("en-US"));
const asset = (p, rel) => (OFF ? `projects/${encodeURIComponent(p.name)}/` : `/p/${encodeURIComponent(p.name)}/`) + rel.split("/").map(encodeURIComponent).join("/");
const tET = (iso) => new Date(iso).toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit", timeZone: "America/New_York" });
const bytes = (b) => (b > 1e6 ? (b / 1e6).toFixed(1) + " MB" : Math.round(b / 1e3) + " KB");

/* ---------- avatar shapes ---------- */
const SHAPES = {
  circle: '<circle cx="22" cy="22" r="17"/>',
  blob: '<path d="M22 5c9 0 17 6 17 15s-5 19-16 19S5 33 5 22 13 5 22 5z"/>',
  pebble: '<ellipse cx="22" cy="23" rx="18" ry="14"/>',
  teardrop: '<path d="M22 4C22 4 37 20 37 28a15 15 0 0 1-30 0C7 20 22 4 22 4z"/>',
  cloud: '<path d="M13 34a8 8 0 0 1-1-16 11 11 0 0 1 21-2 9 9 0 0 1 0 18z"/>',
  wedge: '<path d="M6 36L22 6l16 30z" stroke-linejoin="round"/>',
  squircle: '<rect x="5" y="5" width="34" height="34" rx="12"/>',
  tablet: '<rect x="9" y="4" width="26" height="36" rx="6"/>',
  hex: '<path d="M22 4l16 9v18l-16 9-16-9V13z"/>',
  sparkle: '<path d="M22 3c2 10 7 15 17 19-10 2-15 7-17 19-2-12-7-17-17-19 10-4 15-9 17-19z"/>',
};
const avatar = (b, size = 46) => `<svg width="${size}" height="${size}" viewBox="0 0 44 44"><g fill="${b.color}" stroke="#ffffff33" stroke-width="1.5">${SHAPES[b.shape] || SHAPES.circle}</g><text x="22" y="27" font-size="13" font-weight="800" text-anchor="middle" fill="#0b0f1f" opacity=".75">${esc((b.name.match(/[A-Z]/g) || [b.name[0]]).slice(0, 2).join(""))}</text></svg>`;

/* ---------- views ---------- */
function statusPill(p) {
  if (!p.port) return `<span class="pill"><span class="dot na"></span>no port</span>`;
  if (OFF) return `<span class="pill"><span class="dot na"></span>:${p.port} · ${p.status && p.status.live ? "was live when bundled" : "was offline when bundled"}</span>`;
  return p.status && p.status.live ? `<span class="pill"><span class="dot live"></span>Live · :${p.port}</span>` : `<span class="pill"><span class="dot off"></span>Offline · :${p.port}</span>`;
}
function projectsView() {
  const ps = D.projects, t = D.story.totals, ready = ps.filter((p) => p.ready).length;
  const live = OFF ? null : ps.filter((p) => p.status && p.status.live).length;
  return `
  <div class="stats">
    <div class="stat"><div class="v">${ps.length}</div><div class="l">project folders found <span class="mtag">MEASURED</span></div></div>
    <div class="stat"><div class="v">${ready}</div><div class="l">ready (README + offline snapshot)</div></div>
    <div class="stat"><div class="v">${live == null ? "—" : live}</div><div class="l">${OFF ? "live status (box only)" : "answering on their ports right now"}</div></div>
    <div class="stat"><div class="v">${fmt(t.loc)}</div><div class="l">lines of code (incl. hub)</div></div>
    <div class="stat"><div class="v">${fmt(t.screenshots)}</div><div class="l">screenshots &amp; clips</div></div>
    <div class="stat"><div class="v">${fmt(t.tests)}</div><div class="l">test files</div></div>
  </div>
  <div class="projects">${ps.map((p) => {
    const cover = p.cover ? `style="background-image:url('${asset(p, p.cover)}')"` : "";
    const snap = p.snapshots[0];
    const miss = [!p.hasReadme && "README", !p.snapshots.length && "offline snapshot"].filter(Boolean);
    return `<article class="pcard" data-project="${esc(p.name)}">
      <div class="cover ${p.cover ? "" : "empty"}" ${cover}>${p.cover ? "" : "<span>no screenshot yet</span>"}<div class="status">${statusPill(p)}</div>
        <div class="badge">${p.ready ? '<span class="pill" style="color:#a7f3d0">✓ Ready</span>' : '<span class="pill" style="color:#fde68a">🛠 Still building</span>'}</div></div>
      <div class="pbody"><h2>${esc(p.title)}</h2>
        <div class="pitch">${p.pitch ? esc(p.pitch) : '<span class="mut">No README yet, so no pitch. TokenMax is probably still building this one.</span>'}</div>
        <div class="counts"><span><b>${fmt(p.counts.files)}</b> files</span><span><b>${fmt(p.counts.loc)}</b> LOC</span><span><b>${p.counts.screenshots}</b> screenshots</span><span><b>${p.counts.tests}</b> tests</span>${p.videos.length ? `<span><b>${p.videos.length}</b> video${p.videos.length > 1 ? "s" : ""}</span>` : ""}<span class="mut">${esc(p.name)}/</span></div>
        ${miss.length ? `<div class="missing">Missing: ${miss.join(" + ")}</div>` : ""}
        <div class="btns">
          ${p.port ? `<a class="btn primary" href="http://127.0.0.1:${p.port}/" target="_blank" rel="noopener">${OFF ? "Live on the box" : "Open live"} :${p.port} ↗</a>` : `<span class="btn disabled">No live port</span>`}
          ${snap ? `<a class="btn" href="${asset(p, snap)}" target="_blank">Offline snapshot (${bytes(p.snapshotBytes)})</a>` : `<span class="btn disabled">No snapshot yet</span>`}
          ${p.hasReadme ? `<a class="btn" href="${asset(p, "README.md")}" target="_blank">README</a>` : ""}
          ${p.videos.map((v, i) => `<a class="btn" href="${asset(p, v)}" target="_blank" title="${esc(v)}">▶ ${esc(v.split("/").pop().replace(/\.[^.]+$/, "").slice(0, 28))}</a>`).slice(0, 3).join("")}
        </div></div></article>`;
  }).join("")}</div>`;
}

function storyView() {
  const st = D.story, u = st.usage;
  const t0 = new Date(st.start).getTime(), t1 = Math.max(new Date(st.end).getTime(), t0 + 4 * 3600e3);
  const W = 1000, L = 150, H = 34 * st.lanes.length + 50;
  const R = 30, X = (ms) => L + ((ms - t0) / (t1 - t0)) * (W - L - R);
  const colors = ["#22d3ee", "#a78bfa", "#f472b6", "#34d399", "#fbbf24", "#60a5fa"];
  let svg = `<svg class="timeline" viewBox="0 0 ${W} ${H}">`;
  for (let ms = t0; ms <= t1; ms += 30 * 60e3) { const x = X(ms); svg += `<line x1="${x}" x2="${x}" y1="10" y2="${H - 22}" stroke="#ffffff12"/><text x="${x}" y="${H - 6}" fill="#9aa5c4" font-size="11" text-anchor="middle">${tET(new Date(ms).toISOString())}</text>`; }
  const maxB = Math.max(1, ...st.lanes.flatMap((l) => Object.values(l.buckets)));
  st.lanes.forEach((l, i) => {
    const y = 14 + i * 34, c = colors[i % colors.length];
    svg += `<text x="${L - 10}" y="${y + 17}" fill="#eef1fb" font-size="12.5" font-weight="700" text-anchor="end">${esc(l.project)}</text><rect x="${L}" y="${y + 4}" width="${W - L - R}" height="22" rx="6" fill="#ffffff06"/>`;
    Object.entries(l.buckets).forEach(([k, n]) => { const a = t0 + k * st.bucketMinutes * 60e3; svg += `<rect x="${X(a)}" y="${y + 4}" width="${Math.max(2, X(a + st.bucketMinutes * 60e3) - X(a) - 1)}" height="22" rx="3" fill="${c}" opacity="${0.25 + 0.75 * Math.sqrt(n / maxB)}"><title>${esc(l.project)} · ${tET(new Date(a).toISOString())}: ${n} file(s) last modified</title></rect>`; });
    st.milestones.filter((m) => m.project === l.project).forEach((m) => { const x = X(new Date(m.at).getTime()); svg += `<path d="M${x} ${y} l5 5 -5 5 -5 -5z" fill="#fff"><title>${esc(m.what)} · ${tET(m.at)}</title></path>`; });
  });
  const nx = X(new Date(st.now).getTime());
  svg += `<line x1="${nx}" x2="${nx}" y1="6" y2="${H - 22}" stroke="#f472b6" stroke-width="2" stroke-dasharray="4 3"/><text x="${nx + 4}" y="12" fill="#f472b6" font-size="11" font-weight="700">${OFF ? "bundled" : "now"} ${tET(st.now)}</text>`;
  const r7 = X(new Date("2026-10-07T19:00:00-04:00").getTime());
  if (r7 < W) svg += `<line x1="${r7}" x2="${r7}" y1="6" y2="${H - 22}" stroke="#fbbf24" stroke-width="1.5"/><text x="${r7 - 4}" y="12" fill="#fbbf24" font-size="11" text-anchor="end">7:00 PM wrap</text>`;
  svg += "</svg>";
  const tot = st.totals;
  return `
  <div class="stats">
    <div class="stat"><div class="v">${st.lanes.length}</div><div class="l">folders built tonight <span class="mtag">MEASURED</span></div></div>
    <div class="stat"><div class="v">${fmt(tot.files)}</div><div class="l">files (vendored deps excluded)</div></div>
    <div class="stat"><div class="v">${fmt(tot.codeFiles)}</div><div class="l">code files</div></div>
    <div class="stat"><div class="v">${fmt(tot.loc)}</div><div class="l">lines of code</div></div>
    <div class="stat"><div class="v">${fmt(tot.screenshots)}</div><div class="l">screenshots &amp; clips</div></div>
    <div class="stat"><div class="v">${fmt(tot.tests)}</div><div class="l">test files</div></div>
  </div>
  <div class="grid2">
    <div class="card"><h3>Build session timeline (ET) <span class="mtag">MEASURED</span></h3><div class="mut small" style="margin-bottom:6px">Each block is 5 minutes, shaded by how many files in that folder were last modified then. ◆ marks a milestone (README, snapshot export, first screenshot).</div>${svg}
      <div class="mut tiny">${esc(st.note)}</div></div>
    <div class="card"><h3>Why tonight? (usage.json)</h3>${u ? `
      <div style="font-size:30px;font-weight:850">${u.used_pct}% <span class="mut" style="font-size:14px;font-weight:500">used</span></div>
      <div class="gauge"><i style="width:${u.used_pct}%"></i></div>
      <div class="small">${esc(u.label)}. Resets <b>${esc(u.reset_date)}</b>${u.reset_at ? " at " + esc(u.reset_at) : ' (exact time not shown; the earliest it could land is 8 PM ET tonight)'}.</div>
      <div class="mut tiny">Checked ${esc(u.checked_at)} · ${esc(u.source)}</div>` : '<div class="mut">usage.json not found</div>'}
      <h3 style="margin-top:14px">Milestones</h3>
      ${st.milestones.map((m) => `<div class="ms"><span class="t">${tET(m.at)}</span><span><b>${esc(m.project)}</b> · ${esc(m.what)}</span></div>`).join("")}
    </div>
  </div>
  <div class="card" style="margin-top:16px"><h3>Per project <span class="mtag">MEASURED</span></h3><table><thead><tr><th>Project</th><th class="n">Files</th><th class="n">Code files</th><th class="n">Lines of code</th><th class="n">Screenshots</th><th class="n">Tests</th><th class="n">Size</th><th>First file touched</th><th>Last file touched</th></tr></thead><tbody>
  ${st.lanes.map((l) => `<tr><td><b>${esc(l.project)}</b></td><td class="n">${fmt(l.counts.files)}</td><td class="n">${fmt(l.counts.codeFiles)}</td><td class="n">${fmt(l.counts.loc)}</td><td class="n">${fmt(l.counts.screenshots)}</td><td class="n">${fmt(l.counts.tests)}</td><td class="n">${bytes(l.counts.bytes)}</td><td>${l.first ? tET(l.first) : "—"}</td><td>${l.last ? tET(l.last) : "—"}</td></tr>`).join("")}
  </tbody></table><div class="mut tiny" style="margin-top:6px">LOC = lines in .py/.js/.mjs/.ts/.html/.css/.sh outside dist/, data/, out/, screenshots/, vendored folders and build bundles over 200 KB. Tests = files in tests/ or named test_*/smoke*. Screenshots = images and clips in screenshots/. "First file touched" is the oldest surviving mtime, so a project may have started earlier.</div></div>`;
}

function botsView() {
  const bs = D.bots;
  return `
  <div class="note">Each card opens that bot in the Grok Bot app via <code>grokbot://app/v1/agent?id=…</code>, using the real agent id from <code>/home/box/agent-data/agents/&lt;id&gt;/profile.json</code>. The link only works on a device with the Grok Bot app installed. Schedules come from Bot Island's fleet data (generated ${D.fleetGeneratedAt ? esc(new Date(D.fleetGeneratedAt).toLocaleString("en-US", { month: "short", day: "numeric", hour: "numeric", minute: "2-digit", timeZone: "America/New_York" })) + " ET" : "unknown"}). Struck-through routines are paused; dashed chips are output times seen in files, not cron jobs.</div>
  <div class="bots">${bs.map((b) => `<div class="bcard" style="--c:${b.color}">
    <div class="bhead">${avatar(b)}<div><div class="bname">${esc(b.name)}</div><div class="brole">${esc(b.role || (b.roleFrom === "description" ? b.oneLiner : "No title or description yet"))}</div></div></div>
    ${b.role && b.oneLiner ? `<div class="bline">${esc(b.oneLiner)}</div>` : ""}
    <div class="chips">${b.schedule.map((s) => `<span class="chip">⏰ ${esc(s)}</span>`).join("")}${b.paused.map((s) => `<span class="chip paused">${esc(s)}</span>`).join("")}${b.rhythm.map((s) => `<span class="chip obs">👀 ${esc(s)}</span>`).join("")}${!b.schedule.length && !b.rhythm.length ? `<span class="chip">💬 ${b.inBotIsland ? "On demand (no active routines in Bot Island data)" : "Not in Bot Island data yet"}</span>` : ""}</div>
    <div class="idrow">${esc(b.id)}</div>
    <a class="btn primary" href="${esc(b.deeplink)}">Open in Grok Bot ↗</a></div>`).join("")}</div>`;
}

function render() {
  document.querySelectorAll("#tabs button").forEach((b) => b.classList.toggle("on", b.dataset.tab === S.tab));
  $("#app").innerHTML = ({ projects: projectsView, story: storyView, bots: botsView }[S.tab] || projectsView)();
  const u = D.story.usage;
  $("#fuel").innerHTML = u ? `<div class="l">${esc(u.label)}</div><div class="v">${u.used_pct}% used</div><div class="gauge"><i style="width:${u.used_pct}%"></i></div><div class="l">resets ${esc(u.reset_date)} · checked ${tET(u.checked_at.replace(/T(\d\d:\d\d)-/, "T$1:00-"))} ET</div>` : "";
  $("#foot").innerHTML = `${OFF ? "Offline bundle" : "Live hub"} · scanned ${tET(D.generatedAt)} ET · ${D.projects.length} projects · ${D.bots.length} bots · built by TokenMax on Oct 7, 2026`;
}
document.getElementById("tabs").addEventListener("click", (e) => { const b = e.target.closest("button"); if (!b) return; S.tab = b.dataset.tab; history.replaceState(null, "", "#" + S.tab); render(); });
(async function boot() {
  try {
    D = window.HUB_SNAPSHOT || (await (await fetch("/api/hub")).json());
    render();
    if (!OFF) setInterval(async () => { try { D = await (await fetch("/api/hub")).json(); if (S.tab !== "bots") render(); } catch (e) {} }, 30000);
  } catch (err) { $("#app").innerHTML = `<div class="loading">Failed to load: ${esc(err.message)}</div>`; }
})();
