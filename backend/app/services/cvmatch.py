"""Instant CV-vs-posting match, computed locally from the WHOLE CV (not just the skills list).

`build(cv)` boils the CV down to a small, private-ish summary kept in the user's profile: the technologies it mentions, its role titles, the
words it uses, years of experience, languages. `score(...)` compares a posting against that summary and returns (0-100, reason):
  * requirements  : technologies / skills the posting asks for that the CV evidences (title mentions count more)
  * role          : how close the posting's title is to roles you held, plus words the posting shares with the CV
  * level         : seniority asked for (years) against the years in the CV
  * place/language: city or remote, Dutch required when the CV lists no Dutch
It is the cheap first read. The AI score reads the same CV and the same posting in full and replaces it when you run it."""
import re, datetime as dt, functools

_TOK = re.compile(r"[a-z0-9+#][a-z0-9+#.]*[a-z0-9+#]|[a-z0-9+#]")
_STOP = set("the and for with you your our are will this that from have has was were been their they them who what when which also into over more most such than then there these those about other some any all can may must should would could per via not but out off its it's let get got new use used using work works working team teams role job jobs company companies join looking seek seeking candidate candidates experience years year skills ability strong good great excellent knowledge understanding responsible responsibilities requirements required plus preferred nice bonus including well within across between while where how why each both either neither across ensure support provide provides providing help helping make making build building develop developing development developer engineer engineers software engineering design senior junior lead manager principal specialist consultant projects project een het van voor met bij onze jij wij zijn ben bent wordt worden naar door als maar dan ook niet wel meer deze die dat".split())
_LEVEL = [("intern", 0), ("junior", 1), ("graduate", 1), ("medior", 3), ("mid", 3), ("senior", 5), ("lead", 7), ("principal", 8), ("staff", 8), ("head of", 8), ("manager", 5), ("director", 10)]


def _words(text: str) -> list[str]:
    return [w.strip(".") for w in _TOK.findall((text or "").lower().replace("-", " ")) if len(w.strip(".")) >= 3]


@functools.lru_cache(maxsize=8192)
def _terms(text: str) -> frozenset:
    """Technology terms of the shared vocabulary in `text`, by n-gram lookup (fast: no regex per term)."""
    from app.cvtools import cv as cvmod
    ws = [w.rstrip(".") for w in _TOK.findall((text or "").lower().replace("-", " "))]
    out = set()
    for i, w in enumerate(ws):
        for n in (1, 2):
            g = " ".join(ws[i:i + n])
            if g in cvmod.VOCAB: out.add(g)
    return frozenset(out)


def _years(cv: dict) -> float:
    now = dt.date.today().year; lo, hi = 9999, 0
    for b in cv.get("experience") or []:
        ys = [int(y) for y in re.findall(r"(?<!\d)(?:19|20)\d{2}(?!\d)", str(b.get("date", "")))]
        if re.search(r"present|current|now|today|heden", str(b.get("date", "")), re.I): ys.append(now)
        if ys: lo, hi = min(lo, min(ys)), max(hi, max(ys))
    return float(max(0, hi - lo)) if hi else 0.0


def build(cv: dict | None) -> dict:
    """Summary of the whole CV for fast matching. Empty dict when there is no CV."""
    if not cv: return {}
    from app.cvtools import cv as cvmod
    text = cvmod.cv_text_for_gaps(cv)
    skills = [str(s) for s in (cv.get("skills") or [])] + [str(x) for g in cv.get("skill_groups") or [] for x in (g.get("items") or [])]
    titles = [str(b.get("title") or "") for b in (cv.get("experience") or []) if b.get("title")] + [str(b.get("title") or "") for b in (cv.get("projects") or []) if b.get("title")]
    freq: dict[str, int] = {}
    for w in _words(text + " " + " ".join(skills)):
        if w not in _STOP and not w.isdigit(): freq[w] = freq.get(w, 0) + 1
    words = [w for w, _ in sorted(freq.items(), key=lambda x: -x[1])][:500]
    langs = " ".join(map(str, cv.get("languages") or [])).lower()
    return {"terms": sorted(set(_terms(text)) | {s.lower() for s in skills if len(s) < 40}), "titles": titles[:12], "words": words, "years": _years(cv),
            "dutch": bool(re.search(r"dutch|nederlands|\bnl\b", langs)), "summary_len": len(text)}


def _level(title: str) -> int | None:
    t = title.lower()
    for k, y in _LEVEL:
        if re.search(r"\b" + re.escape(k) + r"\b", t): return y
    return None


def score(title, desc, location, jtype, lang, p, sector=None) -> tuple[int, str]:
    m = (p or {}).get("cv_match") or {}
    if not m: return 0, ""
    t = (title or "").lower(); d = (desc or "")[:6000]
    cvt = set(m.get("terms") or []); cvw = set(m.get("words") or [])
    why: list[str] = []
    # requirements: weighted vocabulary the posting asks for
    tt, dt_ = _terms(title or ""), _terms(d)
    req = {k: 3.0 for k in tt}; [req.setdefault(k, 1.0) for k in dt_]
    have = [k for k in req if k in cvt]; miss = [k for k in req if k not in cvt]
    tot = sum(req.values())
    cov = sum(req[k] for k in have) / tot if tot else None
    # words: for postings without recognised technologies (sales, design, finance ...) compare plain words
    tw = [w for w in dict.fromkeys(_words(title or "")) if w not in _STOP]
    dw = [w for w in dict.fromkeys(_words(d)) if w not in _STOP][:80]
    tws = sum(1 for w in tw if w in cvw) / len(tw) if tw else 0
    dws = sum(1 for w in dw if w in cvw) / len(dw) if dw else 0
    ctitles = [x.lower() for x in m.get("titles") or []]
    ttl = 0.0
    for ct in ctitles:
        cw = {w for w in _words(ct) if w not in _STOP}; jw = {w for w in _words(t) if w not in _STOP}
        if cw and jw: ttl = max(ttl, len(cw & jw) / min(len(cw), len(jw)))
    role = min(1.0, 0.6 * max(ttl, tws) + 0.4 * dws * 2)
    if cov is None: base = 0.55 * role + 0.45 * min(1.0, dws * 2.2)
    else: base = 0.62 * cov + 0.38 * role
    score_ = 100 * base
    if have: why.append("your CV covers: " + ", ".join(have[:6]))
    if miss and cov is not None: why.append("not in your CV: " + ", ".join(miss[:4]))
    if ttl >= 0.5: why.append("similar to a role you held")
    # level
    need = _level(title or ""); yrs = float(m.get("years") or 0)
    if need is not None:
        if need >= 5 and yrs + 1.5 < need: score_ -= min(28, 7 * (need - yrs)); why.append(f"asks for about {need}+ years, your CV shows {yrs:g}")
        elif need <= 1 and yrs >= 6: score_ -= 10; why.append("an entry-level role for your experience")
    if jtype == "internship" and yrs >= 5: score_ -= 8
    # place and language
    cities = [c.lower() for c in (p or {}).get("cities", []) if c.strip()]
    loc = (location or "").lower()
    if cities and any(c in loc for c in cities): score_ += 5; why.append("in your city")
    if sector and (p or {}).get("sectors") and sector not in p["sectors"] and sector != "other": score_ -= 12
    if lang == "dutch_required" and not m.get("dutch"): score_ = min(score_, 40) - 5; why.append("Dutch required, none in your CV")
    if lang == "non_english": score_ = min(score_, 45); why.append("not written in English")
    return max(0, min(100, round(score_))), "; ".join(why) or "little overlap with your CV"
