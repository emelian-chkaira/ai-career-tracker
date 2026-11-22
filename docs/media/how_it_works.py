"""Draws docs/media/how-it-works.svg: the four flows of AI Career Tracker in one infographic.
Run:  python3 docs/media/how_it_works.py   (helpers in infokit.py)."""
from infokit import out, COLORS, t, pill, card, icon, cyl_v, arrow, diamond, node, save

W, H = 1440, 1700
BR, GR, PK, BL, GY = "#b45309", "#15803d", "#be185d", "#1d4ed8", "#64748b"

out.append(f'<rect width="{W}" height="{H}" fill="#ffffff"/>')
t(60, 78, "AI Career Tracker", 46, 900, "#b91c1c", "start")
t(60, 128, "How It Works", 46, 900, "#1d4ed8", "start")
t(62, 158, "① every posting is cleaned once  ·  ② ranked for you  ·  ③ your CV tailored per job  ·  ④ your inbox moves the pipeline", 15, 600, "#475569", "start")
for i, (name, col) in enumerate([("flow", "brown"), ("data", "green"), ("AI", "pink"), ("events", "blue")]):
    x = 1080 + (i % 2) * 150; y = 70 + (i // 2) * 34
    out.append(f'<line x1="{x}" y1="{y}" x2="{x + 34}" y2="{y}" stroke="{COLORS[col]}" stroke-width="3" stroke-dasharray="7 5"/>')
    t(x + 42, y + 5, name, 13, 700, "#334155", "start")

# ------------------------------------------------------------------ ① life of one posting
card(60, 220, 1320, 330, "#a16207", "#fffbeb", "①  The life of one posting:  read → clean → place → classify → fold → index", "#a16207")
y = 310
node(140, y, "📥", "Read", BR, ("ATS JSON · JSON-LD", "HTML · JobSpy boards"))
node(310, y, "✂️", "Clean title", BR, ("link label? title from URL", "or drop it"))
node(480, y, "🌍", "Place", BR, ("countries · city", "work mode · remote scope"))
diamond(650, y - 12, ["Country", "collected?"], "#ca8a04")
node(650, 470, "⛔", "Skip", GY, ("not a collected country",), ring=GY)
node(820, y, "📋", "Classify", BR, ("field · level · language", "salary · skills"))
diamond(990, y - 12, ["Same role at", "employer?"], "#ca8a04")
node(1150, y, "🧩", "Fold", "#c2410c", ("extra place / link", "one role, one card"))
node(1150, 455, "🆕", "Insert", "#c2410c", ("new job",))
node(1305, 385, "🧠", "Index", GR, ("tsvector + embedding", "fastembed ONNX"))
for a, b in ((140, 310), (310, 480)): arrow([(a + 36, y - 12), (b - 36, y - 12)], "brown", dash=False)
arrow([(516, y - 12), (592, y - 12)], "brown", dash=False)
arrow([(706, y - 12), (784, y - 12)], "brown", "yes", dash=False, ly=-18)
arrow([(650, y + 30), (650, 425)], "gray", "no", dash=False, lx=22)
arrow([(856, y - 12), (932, y - 12)], "brown", dash=False)
arrow([(1046, y - 12), (1114, y - 12)], "brown", "yes", dash=False, ly=-18)
arrow([(990, y + 30), (990, 443), (1112, 443)], "brown", "no", at=0.1, dash=False, lx=22)
arrow([(1186, y - 6), (1272, 362)], "green", dash=False)
arrow([(1186, 443), (1272, 385)], "green", dash=False)

# ------------------------------------------------------------------ ② matched to you
card(60, 610, 1320, 430, GR, "#f0fdf4", "②  Matched to your spec and your CV", GR)
arrow([(1305, 478), (1305, 580), (160, 580), (160, 668)], "green", "store", at=0.5, lx=300, ly=-2)
cyl_v(160, 690, 90, 110, "#16a34a", "Open jobs", "career pages + boards")
y = 730
node(420, y, "🔍", "Filter", GR, ("country · city · remote", "level · language · sponsor"))
node(660, y, "📊", "Rank", GR, ("title 30 · skills 35 · field 15", "place 10 · keywords 10"))
node(900, y, "🤖", "AI fit score", PK, ("strengths · gaps · deal-breakers", "capped by hard facts"))
node(1140, y, "🎯", "Your feed", "#c2410c", ("ranked and explained", "one card per role"))
node(1300, y, "🔔", "Alerts", BL, ("daily e-mail", "in-app"), ring="#f59e0b")
arrow([(212, y - 12), (384, y - 12)], "green", dash=False)
arrow([(456, y - 12), (624, y - 12)], "brown", dash=False)
arrow([(696, y - 12), (864, y - 12)], "pink", dash=False)
arrow([(936, y - 12), (1104, y - 12)], "brown", dash=False)
arrow([(1176, y - 12), (1264, y - 12)], "blue", dash=False)
y2 = 940
node(420, y2, "👤", "Your spec", "#ca8a04", ("field · countries · cities", "titles · level · work mode"), ring="#f59e0b")
node(780, y2, "📄", "Your CV", PK, ("skills · experience", "encrypted at rest 🔒"))
arrow([(420, 898), (420, 822)], "violet", "your filters", lx=56)
arrow([(452, 902), (628, 822)], "violet")
arrow([(752, 902), (684, 822)], "violet", "skills", lx=-38)
arrow([(808, 902), (876, 822)], "pink", "CV + job", lx=48)
arrow([(380, 928), (74, 928), (74, 300), (104, 300)], "brown", "new country → find employers", at=0.0, ly=-18)

# ------------------------------------------------------------------ ③ CV studio
card(60, 1100, 640, 540, PK, "#fdf2f8", "③  CV Studio · Reactive Resume · AI tailoring", PK)
y = 1200
node(160, y, "📂", "Import", PK, ("PDF · Word · LaTeX", "Reactive Resume JSON"))
node(380, y, "✏️", "Edit sections", PK, ("live preview", "A4 or Letter"))
node(600, y, "🤖", "Tailor per job", PK, ("summary · bullets", "cover letter"))
y2 = 1400
node(600, y2, "🛡️", "Fact guard", "#b91c1c", ("no new numbers,", "employers or skills"))
node(380, y2, "🖨️", "Tectonic", BR, ("3 LaTeX layouts", "sandboxed, no shell escape"))
node(160, y2, "📤", "Export", GR, ("PDF download", "push to Reactive Resume"))
arrow([(196, y - 12), (344, y - 12)], "pink", dash=False)
arrow([(416, y - 12), (564, y - 12)], "pink", dash=False)
arrow([(600, 1285), (600, 1356)], "pink", dash=False)
arrow([(564, y2 - 12), (416, y2 - 12)], "brown", dash=False)
arrow([(344, y2 - 12), (196, y2 - 12)], "brown", dash=False)
arrow([(632, 1404), (672, 1404), (672, 1170), (636, 1170)], "red", "retry", at=0.5)
t(380, 1560, "Your CV is encrypted at rest and only sent to the", 12, 600, "#9d174d")
t(380, 1578, "AI provider you chose, after you agree.", 12, 600, "#9d174d")

# ------------------------------------------------------------------ ④ AI inbox
card(740, 1100, 640, 540, BL, "#eff6ff", "④  AI inbox moves your pipeline", BL)
y = 1200
node(850, y, "✉️", "Gmail", "#dc2626", ("read-only OAuth", "new since last sync"))
node(1060, y, "🧹", "Pre-filter", BR, ("skip newsletters", "and marketing"))
node(1270, y, "🤖", "Classify", PK, ("LLM → JSON", "category · company · date"))
y2 = 1400
node(1270, y2, "🔗", "Link", GR, ("employer ·", "your tracked job"))
diamond(1060, y2 - 12, ["confident +", "auto-move on?"], "#ca8a04", w=124)
node(850, y2, "🧭", "Move stage", BL, ("applied → interview →", "offer / rejected"))
node(1060, 1530, "💬", "Suggestion", BL, ("in your Inbox",), ring="#f59e0b")
node(850, 1530, "👤", "You", "#ca8a04", ("accept · correct · undo",), ring="#f59e0b")
arrow([(886, y - 12), (1024, y - 12)], "red", dash=False)
arrow([(1096, y - 12), (1234, y - 12)], "pink", dash=False)
arrow([(1270, 1285), (1270, 1356)], "green", dash=False)
arrow([(1234, y2 - 12), (1124, y2 - 12)], "green", dash=False)
arrow([(996, y2 - 12), (886, y2 - 12)], "blue", "yes", dash=False, ly=-18)
arrow([(1060, y2 + 30), (1060, 1486)], "blue", "no", dash=False, lx=22)
arrow([(1024, 1518), (886, 1518)], "blue", dash=False)
t(1060, 1622, "English · Dutch · German  ·  only extracted facts are stored  ·  Gmail token encrypted", 11.5, 600, "#1e3a8a")

save("how-it-works.svg", W, H)
