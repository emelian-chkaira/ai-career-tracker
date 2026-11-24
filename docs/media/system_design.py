"""Draws docs/media/system-design.svg: the AI Career Tracker system design as one infographic.
Run:  python3 docs/media/system_design.py   (helpers in infokit.py)."""
from infokit import out, COLORS, t, pill, card, icon, chip, cyl_h, cyl_v, arrow, save

W, H = 1440, 1640

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
ext = [("🏢", "Career pages", "11 ATS APIs + HTML"), ("💼", "Job boards", "LinkedIn · Indeed · Glassdoor"), ("🗺️", "Open data", "OSM · Wikipedia · NL IND"), ("✉️", "Gmail API", "read-only OAuth"), ("📑", "Reactive Resume", "REST import / push"), ("🖨️", "Tectonic", "LaTeX → PDF, sandboxed")]
for i, (e, a, b) in enumerate(ext):
    cx = 170 + i * 220
    icon(cx, 1530, e, 36, "#64748b"); t(cx, 1563, a, 14, 800); t(cx, 1582, b, 11.5, 600, "#475569")
    if i == 1: t(cx, 1598, "Google Jobs · Bayt", 11.5, 600, "#475569")
arrow([(560, 1402), (190, 1494)], "brown", "crawl", lx=-95, ly=30)
arrow([(1048, 1384), (1048, 1424), (400, 1424), (400, 1494)], "brown", "search boards", at=0.5)
arrow([(1270, 1402), (1270, 1428), (830, 1428), (830, 1494)], "red", "fetch mail", at=0.5, lx=-120)
arrow([(1310, 600), (1420, 600), (1420, 1444), (1060, 1444), (1060, 1494)], "pink", "CV import / PDF", at=0.5, lx=-80, ly=0)

save("system-design.svg", W, H)
