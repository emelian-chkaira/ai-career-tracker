"""Draws docs/media/technical.svg: the technical view of AI Career Tracker (search, task queue, ingest, security, AI scoring, indexes).
Run:  python3 docs/media/technical.py   (helpers in infokit.py), then render the PNG (see README)."""
from xml.sax.saxutils import escape
from infokit import out, COLORS, t, pill, card, chip, arrow, save

W, H = 1440, 1720
MONO = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"


def mono(x, y, s, size=11.5, fill="#334155", anchor="start", weight=600):
    out.append(f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" fill="{fill}" text-anchor="{anchor}" font-family="{MONO}">{escape(s)}</text>')


def box(x, y, w, h, color, fill, title, lines=()):
    out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12" fill="{fill}" stroke="{color}" stroke-width="2"/>')
    out.append(f'<rect x="{x}" y="{y}" width="{w}" height="30" rx="12" fill="{color}"/><rect x="{x}" y="{y + 18}" width="{w}" height="12" fill="{color}"/>')
    t(x + w / 2, y + 21, title, 13.5, 800, "#fff")
    for i, s in enumerate(lines): mono(x + 11, y + 52 + i * 19, s)


out.append(f'<rect width="{W}" height="{H}" fill="#ffffff"/>')
t(60, 78, "AI Career Tracker", 46, 900, "#b91c1c", "start")
t(60, 128, "Under the Hood", 46, 900, "#1d4ed8", "start")
t(62, 158, "hybrid search  ·  SKIP LOCKED task queue  ·  ingest pipeline  ·  auth and encryption  ·  AI scoring with hard caps  ·  indexes", 15, 600, "#475569", "start")

# ------------------------------------------------------------------ A: search
card(60, 220, 1320, 350, "#4338ca", "#eef2ff", "A · One search, three engines fused:  GET /api/v1/jobs?q=…&mode=…", "#4338ca")
box(80, 270, 205, 125, "#b45309", "#fffbeb", "Query", ["q = 'flutter'", "mode: hybrid | exact", "  | keyword | semantic", "+ filters, sort"])
box(315, 270, 205, 125, "#0e7490", "#ecfeff", "Concept expansion", ["flutter → dart, ios,", "  android, cross-platform", "strong vs related terms", "exact: the label only"])
box(560, 258, 235, 120, "#15803d", "#f0fdf4", "Keyword candidates", ["tsvector (GIN) weighted", "pg_trgm typo clause", "up to 800 · score >= 25", "title > description"])
box(560, 400, 235, 120, "#be185d", "#fdf2f8", "Semantic candidates", ["fastembed ONNX, 384-d", "pgvector HNSW, cosine", "top 150 · min_sim 0.6", "found by meaning"])
box(835, 330, 215, 125, "#7c3aed", "#f5f3ff", "Reciprocal Rank Fusion", ["score = 1/(60+rank_kw)", "      + 1/(60+rank_sem)", "one list, no weights", "to tune"])
box(1090, 330, 270, 125, "#1d4ed8", "#eff6ff", "Order + explain", ["relevance | newest |", "oldest | salary | ai_fit", "matched = why it matched", "facets for the filters"])
arrow([(284, 332), (314, 332)], "brown", dash=False)
arrow([(520, 320), (558, 318)], "teal", dash=False); arrow([(520, 345), (558, 458)], "teal", dash=False)
arrow([(796, 318), (834, 372)], "green", dash=False); arrow([(796, 460), (834, 420)], "pink", dash=False)
arrow([(1051, 392), (1089, 392)], "violet", dash=False)
chip(1040, 520, "Smart = hybrid · Exact = LinkedIn-style · Related = keyword · Meaning = semantic", "#e0e7ff", size=11)

# ------------------------------------------------------------------ B: queue
card(60, 610, 640, 410, "#0e7490", "#ecfeff", "B · Task queue and worker:  tasks table, SKIP LOCKED", "#0e7490")
box(72, 660, 190, 120, "#b45309", "#fffbeb", "API / scheduler", ["INSERT INTO tasks", "  status = 'queued'", "scan · discover · boards", "mail_sync · tailor_cv"])
box(280, 660, 190, 120, "#0e7490", "#ecfeff", "Claim one task", ["UPDATE … WHERE id =", " (SELECT … FOR UPDATE", "  SKIP LOCKED LIMIT 1)", "RETURNING id"])
box(488, 660, 200, 120, "#15803d", "#f0fdf4", "Worker pool", ["ThreadPool: N sites", "at once, one browser", "pool, crawl memory", "run more containers"])
arrow([(264, 722), (278, 722)], "brown", dash=False); arrow([(472, 722), (486, 722)], "teal", dash=False)
box(72, 830, 190, 120, "#be185d", "#fdf2f8", "Handlers", ["HANDLERS = {scan_all,", " discover, board_search,", " embed, mail_sync,", " tailor_cv, …}"])
box(280, 830, 190, 120, "#b91c1c", "#fef2f2", "Heartbeat", ["own thread, every 10 s", "state: running | paused", "  | stopped", "task + note in the DB"])
box(488, 830, 200, 120, "#7c3aed", "#f5f3ff", "Safe stop", ["Ctrl+C: finish the step", "drop queued scans", "exit in <= 30 s even if", "a page read hangs"])
arrow([(580, 782), (580, 828)], "green", dash=False); arrow([(264, 890), (278, 890)], "pink", dash=False); arrow([(472, 890), (486, 890)], "red", dash=False)
chip(380, 995, "pause, resume and stop from the Crawler page, between steps", "#cffafe", size=12)

# ------------------------------------------------------------------ C: ingest
card(740, 610, 640, 410, "#a16207", "#fffbeb", "C · Ingest: one posting from page to index", "#a16207")
box(752, 660, 190, 120, "#b45309", "#fff7ed", "1 · Read", ["11 ATS adapters (JSON)", "JSON-LD · HTML", "JobSpy boards, opt-in", "robots.txt · rate limits"])
box(960, 660, 190, 120, "#b45309", "#fff7ed", "2 · Clean + place", ["title from link label", "countries · city", "work mode · remote scope", "skip: not collected"])
box(1168, 660, 200, 120, "#b45309", "#fff7ed", "3 · Classify", ["field · level · language", "salary · skills", "job type, new or old", "stage (intern, grad)"])
arrow([(944, 722), (958, 722)], "brown", dash=False); arrow([(1152, 722), (1166, 722)], "brown", dash=False)
box(752, 830, 190, 120, "#c2410c", "#fff7ed", "4 · Fold", ["same role at employer?", "one card, every link", "and city kept", "dedupe_jobs task"])
box(960, 830, 190, 120, "#15803d", "#f0fdf4", "5 · Index", ["search_vector (GIN)", "embedding (HNSW)", "title trigram (GIN)", "embeddings worker"])
box(1168, 830, 200, 120, "#64748b", "#f8fafc", "6 · Expire", ["gone from the page →", "deleted after 60 days", "saved jobs never", "deleted"])
arrow([(1268, 782), (1268, 800), (846, 800), (846, 828)], "brown", dash=False)
arrow([(944, 890), (958, 890)], "orange", dash=False); arrow([(1152, 890), (1166, 890)], "green", dash=False)
chip(1060, 995, "Python 3.12 · httpx · BeautifulSoup + lxml · Playwright Chromium", "#fef3c7", size=12)

# ------------------------------------------------------------------ D: security
card(60, 1060, 640, 460, "#7c3aed", "#f5f3ff", "D · Auth, secrets and sandboxing", "#7c3aed")
rows = [("passwords", "argon2id", "#be185d"), ("access token", "JWT, 30 min", "#1d4ed8"), ("refresh token", "opaque, rotating, 30 days", "#15803d"),
        ("sign-in", "e-mail · Google · Firebase (optional)", "#f59e0b"), ("secrets at rest", "Fernet: CV, Gmail token, AI keys", "#7c3aed"),
        ("browser", "keys are never sent back to it", "#0e7490"), ("crawler", "robots.txt, spaced requests, back-off", "#b45309"),
        ("CV compile", "Tectonic, sandbox, no shell escape", "#b91c1c"), ("Gmail", "read-only OAuth, facts only stored", "#dc2626")]
for i, (a, b, c) in enumerate(rows):
    y = 1110 + i * 43
    out.append(f'<rect x="80" y="{y}" width="600" height="36" rx="9" fill="#fff" stroke="{c}" stroke-opacity=".5"/><rect x="80" y="{y}" width="150" height="36" rx="9" fill="{c}"/>')
    mono(155, y + 23, a, 12, "#fff", "middle", 800); mono(244, y + 23, b, 12.5, "#0f172a")

# ------------------------------------------------------------------ E: AI scoring
card(740, 1060, 640, 460, "#be185d", "#fdf2f8", "E · AI fit score, capped by hard facts", "#be185d")
t(1060, 1112, "instant estimate when you have no AI model: 0-100", 12.5, 700, "#9d174d")
parts = [(30, "titles", "#b45309"), (35, "skills + CV", "#15803d"), (15, "field", "#7c3aed"), (10, "place", "#0e7490"), (10, "keywords", "#be185d")]
x = 770
for v, name, c in parts:
    w = 5.6 * v
    out.append(f'<rect x="{x}" y="1130" width="{w}" height="40" fill="{c}"/>'); t(x + w / 2, 1155, f"{v}", 16, 800, "#fff"); t(x + w / 2, 1190, name, 11.5, 700, "#334155"); x += w
box(762, 1225, 190, 125, "#be185d", "#fff", "LLM client", ["Ollama · Claude · OpenAI", "Groq · OpenRouter · …", "11 providers, JSON mode", "with fallbacks"])
box(978, 1225, 180, 125, "#b91c1c", "#fff", "Server flags", ["facts known in code:", "Dutch required, CV has", "no Dutch → cap score", "whatever the model says"])
box(1184, 1225, 180, 125, "#15803d", "#fff", "Result", ["score 0-100", "verdict + strengths", "gaps · deal-breakers", "cached per CV hash"])
arrow([(954, 1288), (976, 1288)], "pink", dash=False); arrow([(1160, 1288), (1182, 1288)], "red", dash=False)
box(762, 1385, 602, 100, "#7c3aed", "#f5f3ff", "Fact guard in CV tailoring", ["every number, employer and skill in the tailored CV", "must already exist in your own CV, otherwise it is rejected"])

# ------------------------------------------------------------------ F: indexes + API
card(60, 1560, 1320, 130, "#1d4ed8", "#eff6ff", "F · Data and API surface", "#1d4ed8")
cs = [("ix_jobs_search_vector  GIN", "#15803d"), ("ix_jobs_title_trgm  GIN gin_trgm_ops", "#15803d"), ("ix_jobs_embedding  HNSW vector_cosine_ops", "#be185d"),
      ("~150 REST endpoints · 16 routers · /api/v1", "#1d4ed8"), ("Alembic migrations", "#b45309"), ("pytest on real Postgres: 165", "#0e7490")]
xs = [260, 540, 840, 1130]
for i, (s, c) in enumerate(cs[:3]): chip(300 + i * 360, 1614, s, "#dcfce7" if c == "#15803d" else "#fce7f3", size=12)
for i, (s, c) in enumerate(cs[3:]): chip(300 + i * 360, 1654, s, "#dbeafe" if c == "#1d4ed8" else ("#fef3c7" if c == "#b45309" else "#cffafe"), size=12)

save("technical.svg", W, H)
