"""Reactive Resume v5 (rxresume) <-> our structured CV.

Reactive Resume is the open-source resume builder; its v5 JSON (basics, summary, sections.*.items, metadata) is the de-facto interchange format.
Importing it lets people bring a resume built there; exporting lets them continue there. Rich text in v5 is HTML (<p>, <ul><li>), ours is plain
text with **bold** and [label](url); the converters translate both ways. Written from the public data shape only."""
import re, html, uuid
from html.parser import HTMLParser

VERSION = "rxresume-v5"
LEVELS = {"native": 5, "fluent": 5, "c2": 5, "c1": 4, "advanced": 4, "b2": 3, "upper": 3, "intermediate": 3, "b1": 2, "a2": 1, "elementary": 1, "basic": 1, "a1": 1, "beginner": 1}
NETWORKS = (("linkedin.com", "LinkedIn"), ("github.com", "GitHub"), ("gitlab.com", "GitLab"), ("twitter.com", "Twitter"), ("x.com", "X"), ("medium.com", "Medium"), ("behance.net", "Behance"), ("dribbble.com", "Dribbble"))
_id = lambda: uuid.uuid4().hex[:12]


# ---------------------------------------------------------------- rich text
def _to_html(text: str, bullets: list[str] | None = None) -> str:
    def inline(s: str) -> str:
        s = html.escape(s or "", quote=False)
        s = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", r'<a href="\2">\1</a>', s)
        return re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
    out = f"<p>{inline(text)}</p>" if (text or "").strip() else ""
    if bullets: out += "<ul>" + "".join(f"<li><p>{inline(b)}</p></li>" for b in bullets if (b or "").strip()) + "</ul>"
    return out


class _Plain(HTMLParser):
    """HTML -> (paragraph text, bullet list). Keeps <strong> as **bold** and <a> as [label](url)."""
    def __init__(self): super().__init__(); self.paras: list[str] = []; self.bullets: list[str] = []; self._buf = ""; self._li = 0; self._href: str | None = None; self._lt = ""
    def _flush(self):
        t = re.sub(r"\s+", " ", self._buf).strip()
        if t: (self.bullets if self._li else self.paras).append(t)
        self._buf = ""
    def handle_starttag(self, tag, attrs):
        if tag in ("p", "div", "br"): self._flush()
        elif tag == "li": self._flush(); self._li += 1
        elif tag in ("strong", "b"): self._buf += "**"
        elif tag == "a": self._href = dict(attrs).get("href"); self._lt = self._buf; self._buf = ""
    def handle_endtag(self, tag):
        if tag in ("p", "div"): self._flush()
        elif tag == "li": self._flush(); self._li = max(0, self._li - 1)
        elif tag in ("strong", "b"): self._buf += "**"
        elif tag == "a":
            label = self._buf.strip(); self._buf = self._lt + (f"[{label}]({self._href})" if self._href and label else label); self._href = None
    def handle_data(self, d): self._buf += d


def _from_html(h: str) -> tuple[str, list[str]]:
    if not h: return "", []
    p = _Plain(); p.feed(h); p._flush()
    text = " ".join(p.paras).replace("** **", " ")
    return text, p.bullets


# ---------------------------------------------------------------- ours -> rxresume
def _network(url: str) -> str:
    return next((n for d, n in NETWORKS if d in url), re.sub(r"^https?://(www\.)?", "", url).split("/")[0])


def _site(links: list[dict]) -> dict:
    l = (links or [{}])[0]; return {"url": l.get("url", ""), "label": l.get("label", "")}


def _level(text: str) -> int:
    t = (text or "").lower()
    return next((v for k, v in LEVELS.items() if re.search(rf"\b{k}\b", t)), 0)


def _section(title: str, items: list, columns: int = 1) -> dict: return {"title": title, "columns": columns, "hidden": False, "items": items}


def _item(**kw) -> dict: return {"id": _id(), "hidden": False, **kw}


def to_rx(cv: dict, template: str = "classic", paper: str = "a4") -> dict:
    head = cv.get("header") or {}; links = [l if isinstance(l, str) else l.get("url", "") for l in cv.get("links") or []]; links = [l if l.startswith("http") else "https://" + l for l in links if l]
    tagline = (head.get("tagline") or [""])[0]
    def blocks(bs, kind):
        out = []
        for b in bs or []:
            title = b.get("title") or b.get("heading", ""); place = b.get("place", "")
            if not place and " | " in title: title, place = [x.strip() for x in title.split(" | ", 1)]
            desc = _to_html(b.get("desc", ""), b.get("bullets", [])); site = _site(b.get("links"))
            if kind == "experience": out.append(_item(company=place or title, position=title if place else "", location="", period=b.get("date", ""), website=site, description=desc, roles=[]))
            elif kind == "education": out.append(_item(school=place or title, degree=title if place else "", area="", grade="", location="", period=b.get("date", ""), website=site, description=desc))
            else: out.append(_item(name=title, period=b.get("date", ""), website=site, description=_to_html(" ".join(x for x in (b.get("desc"), b.get("tech")) if x), b.get("bullets", []))))
        return out
    groups = cv.get("skill_groups") or ([{"label": "Skills", "items": cv.get("skills") or []}] if cv.get("skills") else [])
    langs = []
    for s in cv.get("languages") or []:
        m = re.match(r"^\s*([^(:\-–]+?)\s*[(:\-–]\s*(.+?)\)?\s*$", s); name, flu = (m.group(1).strip(), m.group(2).strip()) if m else (s.strip(), "")
        langs.append(_item(language=name, fluency=flu, level=_level(flu)))
    return {
        "version": VERSION, "picture": {"hidden": True, "url": "", "size": 96, "rotation": 0, "aspectRatio": 1, "borderRadius": 0, "borderColor": "", "borderWidth": 0, "shadowColor": "", "shadowWidth": 0},
        "basics": {"name": cv.get("name", ""), "headline": tagline, "email": cv.get("email", ""), "phone": cv.get("phone", ""), "location": cv.get("location", ""),
                   "url": {"url": links[0] if links else "", "label": ""}, "customFields": []},
        "summary": {"title": "Summary", "columns": 1, "hidden": not cv.get("summary"), "content": _to_html(cv.get("summary", ""))},
        "sections": {
            "experience": _section("Experience", blocks(cv.get("experience"), "experience")),
            "education": _section("Education", blocks(cv.get("education"), "education")),
            "projects": _section("Projects", blocks(cv.get("projects"), "project")),
            "skills": _section("Skills", [_item(name=g.get("label", "Skills"), proficiency="", level=0, keywords=list(map(str, g.get("items", [])))) for g in groups]),
            "languages": _section("Languages", langs),
            "certifications": _section("Certifications", [_item(title=c, issuer="", date="", website={"url": "", "label": ""}, description="") for c in cv.get("certifications") or []]),
            "profiles": _section("Profiles", [_item(network=_network(u), username=re.sub(r"^https?://(www\.)?[^/]+/(in/)?", "", u).strip("/"), website={"url": u, "label": ""}) for u in links]),
        },
        "customSections": [], "metadata": {"template": template, "page": {"format": paper}},
    }


# ---------------------------------------------------------------- rxresume -> ours
def looks_like_rx(d) -> bool:
    return isinstance(d, dict) and isinstance(d.get("basics"), dict) and isinstance(d.get("sections"), dict)


def from_rx(d: dict) -> dict:
    """Reactive Resume v5 JSON (as exported, or the `data` field of an API resume) -> our CV dict. Hidden items are skipped."""
    if "data" in d and not looks_like_rx(d) and looks_like_rx(d["data"]): d = d["data"]
    if not looks_like_rx(d): raise ValueError("this does not look like a Reactive Resume export")
    b = d["basics"]; S = d["sections"]
    def items(key): return [i for i in ((S.get(key) or {}).get("items") or []) if isinstance(i, dict) and not i.get("hidden")]
    def link(i): u = (i.get("website") or i.get("url") or {}); return [{"label": u.get("label") or re.sub(r"^https?://(www\.)?", "", u["url"]), "url": u["url"]}] if isinstance(u, dict) and u.get("url") else []
    def block(title, place, date, desc_html, links, kind="entry"):
        text, bullets = _from_html(desc_html)
        return {"heading": "", "title": title, "place": place, "date": date, "meta": "", "links": links, "desc": text, "tech": "", "kind": kind, "bullets": bullets}
    exp = [block(i.get("position") or i.get("company", ""), i.get("company", "") if i.get("position") else "", i.get("period", ""), i.get("description", ""), link(i)) for i in items("experience")]
    for i, r in zip(items("experience"), exp):                                   # multi-role companies: fold the roles into bullets
        for role in i.get("roles") or []:
            t, bl = _from_html(role.get("description", "")); r["bullets"].append(f"{role.get('position', '')} ({role.get('period', '')})".strip() + (f": {t}" if t else "")); r["bullets"] += bl
    edu = [block(" ".join(x for x in (i.get("degree"), i.get("area")) if x) or i.get("school", ""), i.get("school", "") if (i.get("degree") or i.get("area")) else "", i.get("period", ""), i.get("description", ""), link(i)) for i in items("education")]
    prj = [block(i.get("name", ""), "", i.get("period", ""), i.get("description", ""), link(i), "project") for i in items("projects")]
    groups = [{"label": i.get("name", "Skills"), "items": [str(k) for k in (i.get("keywords") or [])] or [i.get("name", "")]} for i in items("skills")]
    skills = list(dict.fromkeys(k for g in groups for k in g["items"] if k))
    langs = [f"{i.get('language', '')} ({i['fluency']})" if i.get("fluency") else i.get("language", "") for i in items("languages")]
    links = [(p.get("website") or {}).get("url") for p in items("profiles")] + [(b.get("url") or {}).get("url")]
    summary_html = (d.get("summary") or {}).get("content", "") if not (d.get("summary") or {}).get("hidden") else ""
    st, sb = _from_html(summary_html)
    order = ["summary", *[k for k, items_ in (("experience", exp), ("education", edu), ("projects", prj)) if items_], "skills", "languages", "certifications"]
    return {"name": b.get("name", ""), "email": b.get("email", ""), "phone": b.get("phone", ""), "location": b.get("location", ""), "links": [u for u in dict.fromkeys(links) if u],
            "header": {"tagline": [b["headline"]] if b.get("headline") else [], "contact": []}, "footer": "", "summary": " ".join([st, *sb]).strip(),
            "skills": skills, "skill_groups": groups if len(groups) > 1 or (groups and groups[0]["label"] != "Skills") else [], "experience": exp, "education": edu, "projects": prj,
            "languages": [l for l in langs if l], "references": [], "certifications": [i.get("title", "") for i in items("certifications") if i.get("title")], "extras": [], "order": order, "titles": {}, "warnings": []}
