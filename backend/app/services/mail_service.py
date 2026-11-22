"""Shared pieces for reading mail. Mailbox access itself lives in gmail_service (Google OAuth, read-only)."""
import re
from bs4 import BeautifulSoup

MAX_BODY = 6000


class MailError(Exception): pass


def html_to_text(html: str) -> str:
    return re.sub(r"\n{3,}", "\n\n", BeautifulSoup(html or "", "lxml").get_text("\n")).strip()
