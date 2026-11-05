"""The canon as material.

The project's active canon files (the ones the corpus index lists as active)
are selected per arrival and enter the configuration as ``document``
transport traces with provenance. They go to the proposer as apparatus
material; they do not go to the uninstructed baseline, whose point is the
inherited grammar without the system. A passage whose heading matches a
term of the arrival is marked consequential, and constraint 3 requires it
to ground at least one cut, otherwise the draft returns: a canon passage
appended as context is the pattern the Incompatibility Constraints name as
context relegation.

Selection is lexical and deliberately simple. It locates candidates; what a
passage does in the formation is the proposer's and the constraints'.
"""

from __future__ import annotations

import glob
import os
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

STOPWORDS = set("""a an and are as at be been but by can could did do does for from had has have how
i if in into is it its me my of on or our so that the their them then there these they this to was
we what when where which who why will with would you your""".split())

HEADING = re.compile(r"^(#{1,3})\s+(.+?)\s*$")
ACTIVE_LINE = re.compile(r"^\s*\d+\.\s+(\S+\.md)")


def tokens(text: str) -> List[str]:
    return [t for t in re.findall(r"[a-z][a-z\-']+", text.lower()) if t not in STOPWORDS and len(t) > 2]


@dataclass
class Section:
    file: str
    heading: str
    text: str
    line: int


@dataclass
class Passage:
    file: str
    heading: str
    text: str
    line: int
    score: int
    consequential: bool
    matched: List[str] = field(default_factory=list)

    def as_record(self) -> Dict[str, Any]:
        return {"file": self.file, "heading": self.heading, "line": self.line, "score": self.score,
                "consequential": self.consequential, "matched": list(self.matched), "text": self.text}


class Corpus:
    def __init__(self, directory: str) -> None:
        self.directory = os.path.abspath(directory)
        self.index_file: Optional[str] = None
        self.files: List[str] = []
        self.sections: List[Section] = []
        self.headers: Dict[str, str] = {}
        self._load()

    def _load(self) -> None:
        indexes = sorted(glob.glob(os.path.join(self.directory, "CBRA_Corpus_Index*.md")))
        active: List[str] = []
        if indexes:
            self.index_file = os.path.basename(indexes[-1])
            with open(indexes[-1], encoding="utf-8") as handle:
                in_active = False
                for line in handle:
                    if line.startswith("## "):
                        in_active = "active" in line.lower()
                        continue
                    m = ACTIVE_LINE.match(line)
                    if in_active and m:
                        active.append(m.group(1))
        if not active:
            active = [os.path.basename(p) for p in sorted(glob.glob(os.path.join(self.directory, "*.md")))
                      if "Corpus_Index" not in p]
        for name in active:
            path = os.path.join(self.directory, name)
            if not os.path.exists(path):
                continue
            self.files.append(name)
            self._split(name, path)

    def _split(self, name: str, path: str) -> None:
        with open(path, encoding="utf-8") as handle:
            lines = handle.read().splitlines()
        self.headers[name] = "\n".join(lines[:6]).strip()
        heading = os.path.splitext(name)[0]
        start = 0
        buffer: List[str] = []
        for i, line in enumerate(lines):
            m = HEADING.match(line)
            if m:
                text = "\n".join(buffer).strip()
                if text:
                    self.sections.append(Section(name, heading, text, start + 1))
                heading = m.group(2)
                start = i
                buffer = []
            else:
                buffer.append(line)
        text = "\n".join(buffer).strip()
        if text:
            self.sections.append(Section(name, heading, text, start + 1))

    def describe(self) -> Dict[str, Any]:
        return {"directory": self.directory, "index": self.index_file, "files": list(self.files),
                "sections": len(self.sections)}

    def select(self, query: str, limit: int = 4) -> List[Passage]:
        terms = tokens(query)
        if not terms:
            return []
        scored: List[Tuple[int, Passage]] = []
        for section in self.sections:
            heading_l = section.heading.lower()
            body_l = section.text.lower()
            score = 0
            matched: List[str] = []
            consequential = False
            for term in terms:
                if term in heading_l:
                    score += 5
                    matched.append(term)
                    if len(term) >= 4:
                        consequential = True
                else:
                    n = min(body_l.count(term), 3)
                    if n:
                        score += n
                        matched.append(term)
            if score:
                scored.append((score, Passage(section.file, section.heading, section.text, section.line,
                                              score, consequential, sorted(set(matched)))))
        scored.sort(key=lambda s: (-s[0], s[1].file, s[1].line))
        return [p for _, p in scored[:limit]]
