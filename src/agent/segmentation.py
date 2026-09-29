"""HTML normalization and responsibility-aware segmentation.

Segments hold character offsets into the *normalized* text, so any later evidence
quote can be located and re-checked (`text[start:end] == segment.text`). If no
reliable heading is found the whole text is kept as one "unclassified" segment
rather than guessing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from bs4 import BeautifulSoup

SEGMENTER_VERSION = "1"

SegmentKind = Literal["intro", "responsibilities", "requirements", "benefits", "about", "other", "unclassified"]

_HTML_HINT = re.compile(r"<\s*/?\s*(p|div|br|li|ul|ol|h[1-6]|strong|b|span|a|em)\b", re.I)
_BLOCK_TAGS = ["p", "div", "li", "ul", "ol", "h1", "h2", "h3", "h4", "h5", "h6", "tr", "table"]


def normalize_text(raw: str) -> str:
    """Plain text with paragraph breaks kept as newlines (HTML stripped if present)."""
    if not raw:
        return ""
    text = raw
    if _HTML_HINT.search(raw):
        soup = BeautifulSoup(raw, "html.parser")
        for br in soup.find_all("br"):
            br.replace_with("\n")
        for li in soup.find_all("li"):
            li.insert(0, "- ")
        for tag in soup.find_all(_BLOCK_TAGS):
            tag.insert_before("\n")
            tag.insert_after("\n")
        text = soup.get_text()
    text = text.replace("\xa0", " ").replace("\r\n", "\n").replace("\r", "\n")
    lines = [re.sub(r"[ \t]+", " ", ln).strip() for ln in text.split("\n")]
    text = "\n".join(lines)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


_HEADING_RULES: list[tuple[SegmentKind, re.Pattern]] = [
    (
        "responsibilities",
        re.compile(
            r"(the )?difference you will make|a typical day|what you.?(ll| will) (do|be doing|work on)|"
            r"responsibilities|your responsibilities|your role|the role|about the (role|job|position)|"
            r"in this role|day.to.day|your impact|your contribution|key duties|duties|"
            r"une journ[ée]e typique|journ[ée]e type|votre contribution",
            re.I,
        ),
    ),
    (
        "requirements",
        re.compile(
            r"your expertise|expertise|requirements|qualifications|preferred qualifications|"
            r"minimum qualifications|what you (should )?(have|bring)|what we.?re looking for|"
            r"you have|about you|who you are|your background|your skills|skills|experience|"
            r"nice to have|bonus points|good to have|preferred experience|we.?d love to hear from you|"
            r"while (it.?s )?not required|votre expertise|votre profil",
            re.I,
        ),
    ),
    (
        "benefits",
        re.compile(
            r"how we.?ll take care of you|benefits|perks|what we offer|compensation|"
            r"pay transparency|salary|pay range|why join",
            re.I,
        ),
    ),
    (
        "about",
        re.compile(
            r"the community you will join|about (us|the team|the company)|why \w+\?|who we are|"
            r"our mission|our commitment|la communaut[ée]|notre engagement",
            re.I,
        ),
    ),
    ("other", re.compile(r"your location|votre emplacement", re.I)),
]

_MAX_HEADING_WORDS = 14


@dataclass(frozen=True)
class Segment:
    kind: SegmentKind
    heading: str | None
    start: int
    end: int
    text: str


def _classify_heading(line: str) -> SegmentKind | None:
    stripped = line.strip()
    if not stripped or stripped.startswith(("-", "*", "•")):
        return None
    body = stripped.rstrip(":").strip()
    if len(body.split()) > _MAX_HEADING_WORDS or body.endswith((".", ";", ",")):
        return None
    for kind, pattern in _HEADING_RULES:
        if pattern.match(body):
            return kind
    return None


def segment(text: str) -> list[Segment]:
    """Split normalized text into segments at recognised headings."""
    if not text.strip():
        return []

    # (offset, heading text, kind) for each heading line
    headings: list[tuple[int, str, SegmentKind]] = []
    pos = 0
    for line in text.split("\n"):
        kind = _classify_heading(line)
        if kind:
            headings.append((pos, line.strip(), kind))
        pos += len(line) + 1

    if not headings:
        return [Segment("unclassified", None, 0, len(text), text)]

    segments: list[Segment] = []

    def add(kind: SegmentKind, heading: str | None, start: int, end: int) -> None:
        chunk = text[start:end]
        stripped = chunk.strip()
        if not stripped:
            return
        start += len(chunk) - len(chunk.lstrip())
        end = start + len(stripped)
        segments.append(Segment(kind, heading, start, end, text[start:end]))

    add("intro", None, 0, headings[0][0])
    for i, (start, heading, kind) in enumerate(headings):
        end = headings[i + 1][0] if i + 1 < len(headings) else len(text)
        add(kind, heading, start, end)
    return segments
