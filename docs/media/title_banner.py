#!/usr/bin/env python3
"""Writes the README title banner: original sources flowing into one list (flat colours, gentle motion).

Run:  python3 docs/media/title_banner.py [out.svg] [kicker]"""
import pathlib, sys

W, H = 1280, 764
DROP = 64                                   # room for the highlight pills above the two panels
FONT = "-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif"
ATS = ["Greenhouse", "Lever", "Workday", "Personio", "Ashby", "Recruitee"]
BOARDS = [("LinkedIn", "#0A66C2"), ("Indeed", "#2557D6"), ("Glassdoor", "#0C8F37"), ("Bayt", "#D9480F")]
TAGS = [("IND sponsor", "#FEF3C7", "#92400E"), None, ("Internship", "#EDE9FE", "#6D28D9")]
ROWS = [("N", "#0D9488", "Backend Developer", "Northwind Labs · from its careers page", "92%"),
        ("T", "#7C3AED", "Data Engineer", "Tulip Energy · from its job system", "87%"),
        ("C", "#0A66C2", "Data Science Intern", "Canal Pay · found on a job board", "81%")]


def text(x, y, s, size, fill="#F8FAFC", weight=400, anchor="start", extra=""):
    return f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" fill="{fill}" text-anchor="{anchor}" {extra}>{s}</text>'


def rise(delay, body):
    return f'<g class="up" style="animation-delay:{delay:.2f}s">{body}</g>'


def banner(kicker: str) -> str:
    out = [f'<rect width="{W}" height="{H}" rx="28" fill="#0F172A"/>']
    # quiet dot grid behind everything
    out.append('<pattern id="g" width="32" height="32" patternUnits="userSpaceOnUse"><circle cx="2" cy="2" r="1.4" fill="#1E293B"/></pattern>'
               f'<rect width="{W}" height="{H}" rx="28" fill="url(#g)"/>')
    out.append(rise(0, text(640, 58, f'<tspan class="dot" fill="#34D399">●</tspan>  {kicker}', 18, "#94A3B8", 700, "middle", 'letter-spacing="3"')))
    out.append(rise(.06, text(640, 136, '<tspan fill="#38BDF8">AI</tspan> Career Tracker', 76, "#F8FAFC", 800, "middle", 'letter-spacing="-2"')))
    out.append(rise(.14, text(640, 196, 'Jobs <tspan fill="#FBBF24">straight from the source.</tspan>', 40, "#F8FAFC", 800, "middle")))

    for i, (x, w, colour, words) in enumerate([(270, 270, "#7C3AED", "🎓 Jobs and internships"), (556, 454, "#B45309", "🇳🇱 Netherlands: IND recognised sponsors")]):
        out.append(rise(.2 + i * .08, f'<rect x="{x}" y="222" width="{w}" height="44" rx="22" fill="{colour}"/>' + text(x + w / 2, 251, words, 19, "#fff", 700, "middle")))
    out.append(f'<g transform="translate(0,{DROP})">')

    # left: where the jobs are fetched from
    out.append(rise(.24, '<rect x="48" y="240" width="500" height="400" rx="22" fill="#162036" stroke="#2A3A57"/>'
                    + text(76, 282, "FETCHED FROM ORIGINAL SOURCES", 15, "#34D399", 800, extra='letter-spacing="2"')
                    + text(76, 322, "Employers’ own career pages", 27, weight=800)
                    + text(76, 352, "read directly, from the job system behind them", 17, "#94A3B8")))
    for i, name in enumerate(ATS):
        x, y = 76 + (i % 3) * 152, 374 + (i // 3) * 50
        out.append(rise(.4 + i * .06, f'<rect x="{x}" y="{y}" width="140" height="38" rx="10" fill="#0F172A" stroke="#34D399" stroke-opacity=".55"/>' + text(x + 70, y + 25, name, 17, "#E2E8F0", 700, "middle")))
    out.append(rise(.78, '<line x1="76" y1="494" x2="520" y2="494" stroke="#2A3A57"/>' + text(76, 528, "+ OPTIONAL JOB-BOARD SEARCHES", 15, "#FBBF24", 800, extra='letter-spacing="2"')))
    for i, (name, colour) in enumerate(BOARDS):
        x, y = 76 + (i % 2) * 230, 546 + (i // 2) * 42
        out.append(rise(.84 + i * .07, f'<rect x="{x}" y="{y}" width="214" height="34" rx="17" fill="{colour}"/>' + text(x + 107, y + 23, name, 17, "#fff", 700, "middle")))

    # middle: the flow
    for i, (y, colour) in enumerate([(330, "#34D399"), (440, "#38BDF8"), (580, "#FBBF24")]):
        d = f"M548 {y} C 630 {y}, 640 440, 722 440"
        out.append(f'<path d="{d}" fill="none" stroke="{colour}" stroke-opacity=".25" stroke-width="3"/>'
                   f'<path class="flow" style="animation-delay:{i * -.4}s" d="{d}" fill="none" stroke="{colour}" stroke-width="3" stroke-linecap="round" stroke-dasharray="4 18"/>')
    out.append(rise(.6, '<circle cx="640" cy="440" r="42" fill="#F8FAFC"/>' + text(640, 436, "one role", 14, "#0F172A", 800, "middle") + text(640, 454, "one card", 14, "#0F172A", 800, "middle")))

    # right: the single ranked list
    out.append(rise(.34, '<rect x="722" y="240" width="510" height="400" rx="22" fill="#F8FAFC"/>'
                    + text(750, 284, "Your one list", 25, "#0F172A", 800) + text(1204, 284, "ranked against your CV", 15, "#64748B", 600, "end")))
    for i, (initial, colour, title, source, score) in enumerate(ROWS):
        y = 306 + i * 92
        out.append(rise(1 + i * .18, f'<rect x="742" y="{y}" width="470" height="78" rx="14" fill="#fff" stroke="#E2E8F0"/>'
                        f'<rect x="758" y="{y + 17}" width="44" height="44" rx="11" fill="{colour}"/>' + text(780, y + 47, initial, 21, "#fff", 800, "middle")
                        + text(818, y + 34, title, 20, "#0F172A", 800) + text(818, y + 58, source, 15, "#64748B")
                        + f'<rect x="1128" y="{y + 23}" width="68" height="32" rx="16" fill="#DCFCE7"/>' + text(1162, y + 45, score, 16, "#15803D", 800, "middle")
                        + (f'<rect x="1012" y="{y + 14}" width="104" height="25" rx="12" fill="{TAGS[i][1]}"/>' + text(1064, y + 31, TAGS[i][0], 13.5, TAGS[i][2], 800, "middle") if TAGS[i] else "")))
    out.append(rise(1.6, text(750, 610, "→ tailor your CV · apply · track replies from your inbox", 16, "#475569", 700)))
    out.append(rise(1.7, text(640, 674, "Illustration with example employers · job boards are off until you switch them on", 14, "#64748B", 400, "middle")))
    out.append("</g>")
    style = ('<style>.up{animation:up .7s cubic-bezier(.22,1,.36,1) both}@keyframes up{from{opacity:0;transform:translateY(18px)}to{opacity:1;transform:none}}'
             '.flow{animation:flow 1.2s linear infinite}@keyframes flow{to{stroke-dashoffset:-44}}.dot{animation:blink 2s ease-in-out infinite}@keyframes blink{50%{opacity:.25}}'
             '@media (prefers-reduced-motion:reduce){.up,.flow,.dot{animation:none}}</style>')
    label = "AI Career Tracker: jobs and internships straight from the source, from employers' own career pages and optional LinkedIn, Indeed, Glassdoor and Bayt searches, with IND recognised sponsor badges for the Netherlands"
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="{label}" font-family="{FONT}">\n{style}\n' + "\n".join(out) + "\n</svg>\n"


if __name__ == "__main__":
    out = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else pathlib.Path(__file__).with_name("title.svg"))
    out.write_text(banner(sys.argv[2] if len(sys.argv) > 2 else "OPEN-SOURCE JOB SEARCH"))
    print("wrote", out.name)
