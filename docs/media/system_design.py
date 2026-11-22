"""Draws docs/media/system-design.svg: the AI Career Tracker system design as one infographic.
Run:  python3 docs/media/system_design.py   (then the PNG is rendered by frontend/docs-media or any browser)."""
from pathlib import Path
from xml.sax.saxutils import escape

W, H = 1440, 1640
out: list[str] = []
COLORS = {"violet": "#8b5cf6", "blue": "#2563eb", "green": "#16a34a", "orange": "#ea580c", "red": "#dc2626", "teal": "#0891b2", "brown": "#a16207", "pink": "#db2777", "gray": "#64748b"}


def t(x, y, s, size=14, weight=600, fill="#0f172a", anchor="middle", italic=False):
    out.append(f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" fill="{fill}" text-anchor="{anchor}"{" font-style=\"italic\"" if italic else ""}>{escape(s)}</text>')


def pill(cx, cy, s, bg, fg="#fff", size=14, pad=12):
    w = len(s) * size * 0.58 + pad * 2
    out.append(f'<rect x="{cx - w / 2}" y="{cy - size}" width="{w}" height="{size * 1.9}" rx="7" fill="{bg}" stroke="#0f172a" stroke-opacity=".15"/>')
    t(cx, cy + size * 0.33, s, size, 800, fg)


def card(x, y, w, h, stroke, fill, title=None, title_bg=None, dash=False):
    out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="16" fill="{fill}" stroke="{stroke}" stroke-width="2.2"{" stroke-dasharray=\"7 6\"" if dash else ""}/>')
    if title: pill(x + w / 2, y, title, title_bg or stroke, size=15)


def icon(cx, cy, emoji, size=40, ring=None):
    if ring: out.append(f'<circle cx="{cx}" cy="{cy - size * 0.32}" r="{size * 0.78}" fill="{ring}" opacity=".18"/>')
    t(cx, cy, emoji, size, 400)


def chip(cx, cy, s, bg, fg="#0f172a", size=12.5):
    w = len(s) * size * 0.56 + 18
    out.append(f'<rect x="{cx - w / 2}" y="{cy - 15}" width="{w}" height="26" rx="13" fill="{bg}" stroke="#0f172a" stroke-opacity=".12"/>')
    t(cx, cy + 3, s, size, 700, fg)


def cyl_h(x, y, w, h, color, label, sub=None):
    """Horizontal cylinder (a queue), like the reference picture."""
    r = h / 2
    out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{color}"/>')
    out.append(f'<ellipse cx="{x}" cy="{y + r}" rx="{r * .45}" ry="{r}" fill="{color}"/>')
    out.append(f'<ellipse cx="{x + w}" cy="{y + r}" rx="{r * .45}" ry="{r}" fill="#fff" stroke="{color}" stroke-width="3"/>')
    out.append(f'<rect x="{x}" y="{y + 6}" width="{w}" height="{h * .18}" fill="#fff" opacity=".25"/>')
    t(x + w / 2, y + h + 22, label, 14, 800)
    if sub: t(x + w / 2, y + h + 40, sub, 12, 500, "#475569")


def cyl_v(cx, y, w, h, color, label, sub=None):
    """Vertical cylinder (a database)."""
    rx, ry = w / 2, w * .16
    out.append(f'<path d="M{cx - rx},{y} v{h} a{rx},{ry} 0 0 0 {w},0 v{-h}" fill="{color}"/>')
    out.append(f'<ellipse cx="{cx}" cy="{y}" rx="{rx}" ry="{ry}" fill="#fff" stroke="{color}" stroke-width="3"/>')
    for k in (h * .38, h * .72): out.append(f'<path d="M{cx - rx},{y + k} a{rx},{ry} 0 0 0 {w},0" fill="none" stroke="#fff" stroke-opacity=".45" stroke-width="2"/>')
    t(cx, y + h + ry + 22, label, 13.5, 800)
    if sub: t(cx, y + h + ry + 39, sub, 11.5, 500, "#475569")


def arrow(pts, color, label=None, at=0.5, both=False, dash=True, lx=0, ly=0, label_bg="#fff7ed"):
    c = COLORS[color]
    d = "M" + " L".join(f"{x},{y}" for x, y in pts)
    out.append(f'<path d="{d}" fill="none" stroke="{c}" stroke-width="3"{" stroke-dasharray=\"9 7\"" if dash else ""} marker-end="url(#m-{color})"{f" marker-start=\"url(#s-{color})\"" if both else ""}/>')
    if label:
        i = max(0, min(len(pts) - 2, int((len(pts) - 1) * at)))
        (x1, y1), (x2, y2) = pts[i], pts[i + 1]
        mx, my = (x1 + x2) / 2 + lx, (y1 + y2) / 2 + ly
        w = len(label) * 6.9 + 16
        out.append(f'<rect x="{mx - w / 2}" y="{my - 13}" width="{w}" height="24" rx="6" fill="{label_bg}" stroke="{c}" stroke-width="1.5" transform="rotate(-4 {mx} {my})"/>')
        out.append(f'<text x="{mx}" y="{my + 4}" font-size="12.5" font-weight="700" fill="{c}" text-anchor="middle" transform="rotate(-4 {mx} {my})">{escape(label)}</text>')


# ------------------------------------------------------------------ canvas, title, legend
out.append(f'<rect width="{W}" height="{H}" fill="#ffffff"/>')
t(60, 78, "AI Career Tracker", 46, 900, "#b91c1c", "start")
t(60, 128, "System Design", 46, 900, "#1d4ed8", "start")
t(62, 158, "jobs from employers + job boards  ·  matched to your spec and CV  ·  AI CV tailoring  ·  AI inbox", 15, 600, "#475569", "start")
for i, (name, col) in enumerate([("request", "violet"), ("data", "green"), ("crawl / tasks", "brown"), ("AI", "pink"), ("events", "blue")]):
    x = 1010 + (i % 3) * 140; y = 70 + (i // 3) * 34
    out.append(f'<line x1="{x}" y1="{y}" x2="{x + 34}" y2="{y}" stroke="{COLORS[col]}" stroke-width="3" stroke-dasharray="7 5"/>')
    t(x + 42, y + 5, name, 13, 700, "#334155", "start")

# ------------------------------------------------------------------ row 1: auth, client, static app
icon(150, 262, "🔐", 52, "#dc2626"); pill(150, 300, "Auth", "#dc2626"); t(150, 330, "JWT · Firebase · Google", 12.5, 600, "#475569")
icon(720, 258, "💻", 58, "#2563eb"); t(775, 250, "📱", 34, 400); pill(720, 300, "Client", "#facc15", "#111827"); t(720, 330, "React 18 + TypeScript · Flutter app", 12.5, 600, "#475569")
icon(1290, 262, "🌐", 52, "#0891b2"); pill(1290, 300, "Static web app", "#0891b2"); t(1290, 330, "Vite build · served by FastAPI", 12.5, 600, "#475569")
arrow([(660, 250), (210, 250)], "violet", "sign in", both=True, ly=-18)
arrow([(780, 250), (1230, 250)], "violet", "load app", both=True, ly=-18)

# ------------------------------------------------------------------ row 2: Caddy
icon(720, 420, "🛡️", 46, "#16a34a"); pill(720, 452, "Caddy · HTTPS reverse proxy", "#15803d")
arrow([(720, 345), (720, 378)], "brown", dash=False)

# ------------------------------------------------------------------ row 3: API gateway with routers
card(130, 500, 1180, 120, "#7c3aed", "#f5f3ff", "FastAPI  ·  /api/v1  (API gateway)", "#6d28d9")
routes = [("🔑 auth", "#fee2e2"), ("🔎 jobs search", "#dbeafe"), ("🎯 me · feed · alerts", "#dcfce7"), ("📄 cv · tailor · rr", "#fce7f3"), ("📬 mail · fit · assistant", "#ffedd5"), ("🕷️ admin · crawler", "#fef9c3")]
for i, (r, bg) in enumerate(routes): chip(230 + i * 196, 572, r, bg)

# ------------------------------------------------------------------ row 4: search, database, AI
card(60, 690, 330, 300, "#2563eb", "#eff6ff", "Hybrid Search", "#1d4ed8")
t(225, 735, "words + meaning, fused (RRF)", 13, 600, "#1e3a8a")
cyl_v(150, 770, 86, 120, "#3b82f6", "Full-text", "tsvector · pg_trgm")
cyl_v(300, 770, 86, 120, "#6366f1", "Vectors", "pgvector HNSW (384-d)")
arrow([(270, 622), (225, 688)], "violet", "search query", lx=-58)

card(450, 690, 540, 300, "#16a34a", "#f0fdf4", "PostgreSQL 16  (source of truth)", "#15803d")
dbs = [("companies · jobs", "one role, one card"), ("users · profiles", "CVs encrypted 🔒"), ("pipeline · alerts", "mail events"), ("kv", "schedule · policy · heartbeat")]
for i, (a, b) in enumerate(dbs): cyl_v(530 + i * 128, 765, 80, 120, ["#16a34a", "#059669", "#0d9488", "#65a30d"][i], a, b)
arrow([(640, 622), (640, 688)], "green", "read / write", both=True, lx=95, ly=-6)

card(1050, 690, 330, 300, "#db2777", "#fdf2f8", "AI layer", "#be185d")
icon(1215, 760, "🤖", 44, "#db2777")
for i, s in enumerate(["fit score · capped by facts", "CV tailoring · fact guard", "inbox classifier (JSON)", "job assistant"]): chip(1215, 805 + i * 34, s, "#fce7f3")
t(1215, 960, "Ollama · Claude · OpenAI · Groq · OpenRouter", 11.5, 700, "#9d174d"); t(1215, 977, "DeepSeek · Qwen · Kimi · GLM · Grok · custom", 11.5, 700, "#9d174d")
arrow([(1020, 622), (1180, 688)], "pink", "prompts → JSON", lx=40)

# ------------------------------------------------------------------ row 5: queues and notifications
cyl_h(200, 1050, 260, 54, "#0e7490", "Task queue", "tasks table · SKIP LOCKED · pause / resume / stop")
cyl_h(700, 1050, 240, 54, "#1d4ed8", "Notification queue", "outbox: in-app + e-mail digest")
icon(1030, 1092, "🔔", 44, "#f59e0b"); pill(1030, 1128, "Notifications", "#2563eb", size=12)
arrow([(942, 1077), (990, 1077)], "blue", dash=False)
arrow([(170, 622), (36, 660), (36, 1077), (186, 1077)], "brown", "start task", at=0.4, lx=48)
arrow([(700, 992), (790, 1044)], "blue", "new matches", lx=40, ly=-14)

# ------------------------------------------------------------------ row 6: the worker
card(60, 1170, 1320, 230, "#a16207", "#fffbeb", "Worker  ·  app.workers.run", "#a16207")
steps = [("⏱️", "Scheduler", "window · heartbeat"), ("🔎", "Discover", "maps · Wikipedia · ATS"), ("🕷️", "Scan pool", "httpx · Playwright"), ("🧩", "Ingest", "places · fields · dedupe"), ("🧠", "Embed", "fastembed ONNX"), ("📬", "Mail sync", "Gmail → LLM")]
for i, (e, a, b) in enumerate(steps):
    cx = 160 + i * 222
    icon(cx, 1262, e, 36, "#f59e0b"); pill(cx, 1294, a, "#b45309", size=13); t(cx, 1324, b, 12, 600, "#78350f")
    if i in (0, 1, 2, 3): arrow([(cx + 58, 1250), (cx + 160, 1250)], "brown", dash=False)
for k in range(3): chip(604 + (k - 1) * 70, 1368, "worker", "#dc2626", "#fff", 12)
t(604, 1395, "up to 40 sites at once · robots.txt · rate limits", 11.5, 600, "#7f1d1d")
chip(1048, 1368, "🌐 board search · JobSpy · back-off", "#fde68a")
arrow([(330, 1146), (330, 1168)], "brown", dash=False)
arrow([(826, 1168), (826, 1150), (640, 1150), (640, 994)], "green", "upsert jobs", at=0.9, lx=-52)
arrow([(1270, 1168), (1215, 992)], "pink", "classify mail", lx=-62)

# ------------------------------------------------------------------ row 7: the outside world
card(60, 1450, 1320, 160, "#64748b", "#f8fafc", dash=True); pill(170, 1450, "Outside world", "#475569", size=14)
ext = [("🏢", "Career pages", "11 ATS APIs + HTML"), ("💼", "Job boards", "LinkedIn · Indeed · Glassdoor"), ("🗺️", "Open data", "OSM · Wikipedia · IND"), ("✉️", "Gmail API", "read-only OAuth"), ("📑", "Reactive Resume", "REST import / push"), ("🖨️", "Tectonic", "LaTeX → PDF, sandboxed")]
for i, (e, a, b) in enumerate(ext):
    cx = 170 + i * 220
    icon(cx, 1530, e, 36, "#64748b"); t(cx, 1563, a, 14, 800); t(cx, 1582, b, 11.5, 600, "#475569")
    if i == 1: t(cx, 1598, "Google Jobs · Bayt", 11.5, 600, "#475569")
arrow([(560, 1402), (190, 1494)], "brown", "crawl", lx=-95, ly=30)
arrow([(1048, 1384), (1048, 1424), (400, 1424), (400, 1494)], "brown", "search boards", at=0.5)
arrow([(1270, 1402), (1270, 1428), (830, 1428), (830, 1494)], "red", "fetch mail", at=0.5, lx=-120)
arrow([(1310, 600), (1420, 600), (1420, 1444), (1060, 1444), (1060, 1494)], "pink", "CV import / PDF", at=0.5, lx=-80, ly=0)

defs = "".join(f'<marker id="m-{n}" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{c}"/></marker>'
               f'<marker id="s-{n}" viewBox="0 0 10 10" refX="2" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{c}"/></marker>' for n, c in COLORS.items())
svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="Inter, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif">'
       f"<defs>{defs}</defs>" + "".join(out) + "</svg>")
Path(__file__).with_name("system-design.svg").write_text(svg)
print("wrote system-design.svg")
