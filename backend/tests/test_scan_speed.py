"""Crawler speed: pooled headless browsers, no double downloads, a weekly internship pass, and remembering the ATS found behind a page."""
import datetime as dt, threading, http.server, functools
import pytest
from sqlalchemy import select
from app.crawler import discovery as d
from app.models import Company, Job
from app.services import ingest_service as ing

LINKS = "".join(f'<a href="/jobs/backend-engineer-{i}">Backend Engineer {i}</a>' for i in range(35))


# ---------------------------------------------------------------- 1. one browser serves many pages
PAGE = """<html><body><div id=list></div><img src="/big.png">
<script>fetch('/api/jobs.json').then(r => r.json()).then(js => { for (const j of js) { const a = document.createElement('a'); a.href = j.url; a.textContent = j.title; document.getElementById('list').appendChild(a); } });</script></body></html>"""


class _H(http.server.BaseHTTPRequestHandler):
    hits: list = []
    def do_GET(self):
        _H.hits.append(self.path)
        if self.path == "/api/jobs.json":
            body, ct = b'[{"title": "Data Engineer", "url": "https://acme.nl/jobs/data-engineer"}, {"title": "Platform Engineer", "url": "https://acme.nl/jobs/platform-engineer"}]', "application/json"
        elif self.path == "/big.png": body, ct = b"\x89PNG", "image/png"
        else: body, ct = PAGE.encode(), "text/html"
        self.send_response(200); self.send_header("Content-Type", ct); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
    def log_message(self, *a): pass


@pytest.fixture()
def site():
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _H); threading.Thread(target=srv.serve_forever, daemon=True).start()
    _H.hits = []
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()


def test_browser_is_reused_and_images_are_skipped(site):
    pytest.importorskip("playwright")
    before = dict(d.stats)
    for _ in range(3):
        jobs, html = d.render_scan(site + "/careers")
        assert {j["url"] for j in jobs} >= {"https://acme.nl/jobs/data-engineer", "https://acme.nl/jobs/platform-engineer"}
        assert f"<!-- xhr {site}/api/jobs.json -->" in html                     # the JSON the page called is visible to ATS detection
    assert d.stats["pages"] - before["pages"] == 3
    assert d.stats["launches"] - before["launches"] <= 1                         # one Chromium for all three pages
    assert "/big.png" not in _H.hits                                             # images are never downloaded


# ---------------------------------------------------------------- 2. no double downloads, internship pass only when asked
@pytest.fixture()
def fake_web(monkeypatch):
    calls = []
    def get(url, json_=False, check_robots=True):
        calls.append(url)
        if url == "https://acme.nl/careers": return f"<html>{LINKS}</html>"
        if url == "https://acme.nl": return '<html><a href="/careers">Careers</a></html>'
        return None
    monkeypatch.setattr(d, "get", get)
    monkeypatch.setattr(d, "render_scan", lambda *a, **k: pytest.fail("no browser needed for a static list"))
    return calls


COMPANY = dict(name="Acme", website="https://acme.nl", careers_url="https://acme.nl/careers", ats="html", ats_slug=None, resolved_via=None)


def test_saved_careers_page_needs_no_homepage(fake_web):
    r = d.scan_company(COMPANY, students=False)
    assert r["students_skipped"] and len(r["jobs"]) == 35
    assert fake_web == ["https://acme.nl/careers"]                                 # one request for the whole scan


def test_internship_pass_reuses_the_careers_page(fake_web):
    r = d.scan_company(COMPANY, students=True)
    assert not r["students_skipped"]
    assert fake_web.count("https://acme.nl/careers") == 1                           # read once, shared with the internship pass
    assert fake_web.count("https://acme.nl") == 1                                   # homepage read once, for its student links


# ---------------------------------------------------------------- 3. the ATS behind a rendered page is remembered
def test_ats_found_after_render_is_saved(monkeypatch):
    monkeypatch.setattr(d, "get", lambda url, json_=False, check_robots=True: "<html><a href='/x'>Open roles</a></html>" if url == "https://acme.nl/careers" else None)
    monkeypatch.setattr(d, "render_scan", lambda url, click=(): ([dict(title="Data Engineer", location="", url="https://acme.nl/x/1", description="", posted_at=None)], "<!-- xhr https://acme.recruitee.com/api/offers -->\n<html></html>"))
    api = [dict(title=f"Engineer {i}", location="Amsterdam", url=f"https://acme.recruitee.com/o/{i}", description="", posted_at=None) for i in range(3)]
    monkeypatch.setitem(d.ADAPTERS, "recruitee", lambda slug: api if slug == "acme" else [])
    r = d.scan_company({**COMPANY, "ats": "playwright"}, students=False)
    assert (r["ats"], r["ats_slug"], len(r["jobs"])) == ("recruitee", "acme", 3)       # next scan: one API call, no browser


# ---------------------------------------------------------------- 4. weekly internship pass, without expiring what it found
def J(title, url): return dict(title=title, location="Amsterdam, Netherlands", url=url, description="", posted_at=None)


def test_skipped_internship_pass_keeps_internships(db, monkeypatch):
    c = ing.add_company(db, "Acme", website="https://acme.nl"); c.careers_url = "https://acme.nl/careers"
    ing.store_jobs(db, c, [J("Backend Engineer", "https://acme.nl/jobs/1"), {**J("Software Engineering Intern", "https://acme.nl/stage/1"), "kind": "internship"}]); db.commit()
    seen = []
    def scan(cd, students=True):
        seen.append(students)
        return dict(website=cd["website"], careers_url=cd["careers_url"], ats="html", ats_slug=None, resolved_via=None, note="generic link extraction",
                    jobs=[J("Backend Engineer", "https://acme.nl/jobs/1")], students_skipped=not students)
    monkeypatch.setattr(d, "scan_company", scan)
    ing.scan_company(db, c.id)                                                       # first scan: the internship pass is due
    assert seen == [True] and c.student_scan_at is not None
    assert db.scalar(select(Job.status).where(Job.url == "https://acme.nl/stage/1")) == "expired"   # it ran and the internship is gone

    db.execute(Job.__table__.update().where(Job.url == "https://acme.nl/stage/1").values(status="open")); db.commit()
    ing.scan_company(db, c.id)                                                       # a day later: pass skipped, internship kept
    assert seen == [True, False]
    assert db.scalar(select(Job.status).where(Job.url == "https://acme.nl/stage/1")) == "open"

    c.student_scan_at = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=8); db.commit()
    ing.scan_company(db, c.id)                                                       # a week later: due again
    assert seen == [True, False, True]


def test_rendered_page_without_postings_backs_off(db, monkeypatch):
    c = ing.add_company(db, "Acme", website="https://acme.nl"); db.commit()
    monkeypatch.setattr(d, "scan_company", lambda cd, students=True: dict(website=cd["website"], careers_url="https://acme.nl/careers", ats="html", ats_slug=None, resolved_via=None,
                                                                           note="careers page rendered, no postings found", jobs=[], students_skipped=False))
    ing.scan_company(db, c.id)
    assert c.fail_count == 1 and c.next_scan - c.last_scan >= dt.timedelta(days=14)


# ---------------------------------------------------------------- 5. crawl memory: dead links are skipped, real pages are remembered
class _Resp:
    def __init__(self, code, text=""): self.status_code, self.text = code, text
    def json(self): return {}


@pytest.fixture()
def web(monkeypatch):
    """A fake internet: {url: (status, body)}; everything else is 404. Records every real request."""
    pages, calls = {}, []
    monkeypatch.setattr(d, "allowed", lambda url: True)
    monkeypatch.setattr(d, "_wait", lambda host: None)
    monkeypatch.setattr(d.client, "get", lambda url, **k: (calls.append(url), _Resp(*pages.get(url, (404, ""))))[1])
    monkeypatch.setattr(d, "render_scan", lambda *a, **k: ([], ""))
    d._gone.clear()
    return pages, calls


def test_dead_links_are_skipped_next_time(web):
    pages, calls = web
    pages["https://acme.nl"] = (200, '<html><a href="/werken-bij">Werken bij</a></html>')
    pages["https://acme.nl/werken-bij"] = (200, f"<html>{LINKS}</html>")
    pages["https://acme.nl/stage"] = (200, "<html>stages</html>")
    c = dict(COMPANY, careers_url=None, ats=None, memory={})
    r1 = d.scan_company(c, students=True)
    assert r1["careers_url"] == "https://acme.nl/werken-bij" and len(r1["jobs"]) == 35
    first = len(calls); mem = r1["memory"]
    assert len(mem["dead"]) > 10 and "https://acme.nl/stage" in mem["student"]["urls"]

    calls.clear()
    r2 = d.scan_company(dict(COMPANY, careers_url=r1["careers_url"], ats="html", memory=mem), students=True)
    assert len(r2["jobs"]) == 35
    assert not any(u in mem["dead"] for u in calls)                                # no request to a known-dead page
    assert len(calls) <= 3 and len(calls) < first                                  # careers page, homepage, the one real internship page
    assert "https://acme.nl/stage" in calls


def test_moved_careers_page_is_forgotten_and_found_again(web):
    pages, calls = web
    pages["https://acme.nl"] = (200, '<html><a href="/jobs">Jobs</a></html>')
    pages["https://acme.nl/jobs"] = (200, f"<html>{LINKS}</html>")
    r = d.scan_company(dict(COMPANY, careers_url="https://acme.nl/old-careers", ats="html", memory={}), students=False)
    assert r["careers_url"] == "https://acme.nl/jobs" and "https://acme.nl/old-careers" in r["memory"]["dead"]


def test_gone_board_is_forgotten(web, monkeypatch):
    pages, calls = web
    pages["https://acme.nl/careers"] = (200, f"<html>{LINKS}</html>")
    r = d.scan_company(dict(COMPANY, ats="greenhouse", ats_slug="acme", memory={}), students=False)
    assert (r["ats"], r["ats_slug"]) == ("html", None) and len(r["jobs"]) == 35       # the Greenhouse board answered 404: no longer tried first


def test_removed_posting_expires(db, client, web):
    pages, calls = web
    c = ing.add_company(db, "Acme", website="https://acme.nl")
    ing.store_jobs(db, c, [J("Backend Engineer", "https://acme.nl/jobs/1"), J("Data Engineer", "https://acme.nl/jobs/2")]); db.commit()
    jid = db.scalar(select(Job.id).where(Job.url == "https://acme.nl/jobs/1"))
    r = client.get(f"/api/v1/jobs/{jid}")                                          # its page now answers 404
    assert r.status_code == 200 and r.json()["status"] == "expired"
    assert db.scalar(select(Job.status).where(Job.url == "https://acme.nl/jobs/2")) == "open"


def test_scan_saves_memory(db, monkeypatch):
    c = ing.add_company(db, "Acme", website="https://acme.nl"); db.commit()
    monkeypatch.setattr(d, "scan_company", lambda cd, students=True: dict(website=cd["website"], careers_url="https://acme.nl/careers", ats="html", ats_slug=None, resolved_via=None, note="generic link extraction",
                        jobs=[J("Backend Engineer", "https://acme.nl/jobs/1")], students_skipped=False, memory={**cd["memory"], "dead": {"https://acme.nl/x": "2026-11-22"}, "_skipped": 3}))
    ing.scan_company(db, c.id); db.refresh(c)
    assert c.scan_memory == {"dead": {"https://acme.nl/x": "2026-11-22"}}
