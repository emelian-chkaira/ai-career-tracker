"""The version of AI Career Tracker and its changelog. Release: bump __version__ here and in frontend/package.json, and add an entry to CHANGELOG.md."""
import re
from pathlib import Path

__version__ = "1.0.2"

_FILE = Path(__file__).resolve().parents[2] / "CHANGELOG.md"          # repo root (the Docker image copies it next to backend/)


def changelog() -> list[dict]:
    """CHANGELOG.md (Keep a Changelog layout) -> [{version, date, sections: {Added: [..], Changed: [..], Fixed: [..]}}], newest first."""
    try: text = _FILE.read_text(encoding="utf8")
    except OSError: return []
    out: list[dict] = []; cur = sec = None
    for line in text.splitlines():
        if m := re.match(r"^##(?!#)\s*\[?([^\]\s]+)\]?(?:\s*-\s*(\S+))?", line):
            cur = {"version": m.group(1), "date": m.group(2) or "", "sections": {}}; out.append(cur); sec = None
        elif cur is not None and (m := re.match(r"^###\s+(.+)$", line)): sec = cur["sections"].setdefault(m.group(1).strip(), [])
        elif cur is not None and sec is not None and (m := re.match(r"^[-*]\s+(.+)$", line)): sec.append(m.group(1).strip())
    return out
