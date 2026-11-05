"""The canon as material.

The project's active canon files (the ones the corpus index lists as active)
are selected per arrival and enter the configuration as ``document``
transport traces with provenance. They go to the proposer as apparatus
material; they do not go to the uninstructed baseline, whose point is the
inherited grammar without the system. A passage whose heading is a canon
term the arrival names is marked consequential, and constraint 3 requires it
to ground at least one cut, otherwise the draft returns: a canon passage
appended as context is the pattern the Incompatibility Constraints name as
context relegation.

Selection is lexical and deliberately simple, but it is indexed by the
canon's own vocabulary rather than by every word of the arrival:

* The glossary's entry headings are the term set (``Agential Cut``,
  ``Transport Inscription``, ``Intra-action`` ...). A term matches an
  arrival only as a whole phrase, after light stemming, so ``intra-active``
  finds ``Intra-action`` while ``cut`` alone does not claim ``Agential Cut``.
* A matched term whose phrase is the heading of a section marks that section
  consequential. Only canon terms do this.
* The remaining words of the arrival score sections by rarity across the
  canon (inverse document frequency), so ``system`` and ``relation`` count
  for little in a canon that is about relations, and a word used in one
  section counts for a lot.
* Nothing is returned below a floor score unless a canon term matched, so an
  arrival that names no canon concept and shares only ordinary words with it
  yields no material rather than four weak passages.

It locates candidates; what a passage does in the formation is the
proposer's and the constraints'.
"""

from __future__ import annotations

import glob
import math
import os
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

STOPWORDS = set("""a an and are as at be been but by can could did do does for from had has have how
i if in into is it its me my of on or our so that the their them then there these they this to was
we what when where which who why will with would you your about also any does mean means tell explain
please thing things just like get got within own system systems term terms define definition
cbra here help write writing need want know make let way use using really something someone anything
actually""".split())

HEADING = re.compile(r"^(#{1,3})\s+(.+?)\s*$")
ACTIVE_LINE = re.compile(r"^\s*\d+\.\s+(\S+\.md)")
WORD = re.compile(r"[a-z][a-z\-']*[a-z]|[a-z]")

# Light stemming: enough to make the canon's morphology meet the arrival's
# ("intra-action" / "intra-active", "cut" / "cuts", "relation" / "relational",
# "configure" / "configuration"). Crude on purpose; the selection test set is
# what says whether it is good enough.
SUFFIXES = ("ations", "ation", "ative", "ively", "ities", "ments", "ment", "ness", "ity", "ive",
            "ions", "ion", "ings", "ing", "ers", "er", "ed", "al", "ly", "es", "s")
ALIASES = {"relata": "relat", "relatum": "relat", "relate": "relat", "relation": "relat"}

TERM_HEADING = 8.0   # a canon term the arrival names is this section's heading
TERM_BODY = 2.0      # the named term occurs in the section body
FLOOR = 4.0          # without a term match: at least two rare words and this much score


def stem(word: str) -> str:
    w = word.lower().replace("-", "").replace("'", "")
    if w in ALIASES:
        return ALIASES[w]
    for _ in range(2):
        for suffix in SUFFIXES:
            if w.endswith(suffix) and len(w) - len(suffix) >= 3:
                w = w[: -len(suffix)]
                break
    if w.endswith("ie"):
        w = w[:-2] + "i"
    elif w.endswith("y") and len(w) > 3:
        w = w[:-1] + "i"
    elif w.endswith("e") and len(w) > 3:
        w = w[:-1]
    return ALIASES.get(w, w)


def stems(text: str) -> List[str]:
    out: List[str] = []
    for w in WORD.findall(text.lower()):
        if w in STOPWORDS or len(w) < 3:
            continue
        out.append(stem(w))
    return out


def tokens(text: str) -> List[str]:
    """Kept for callers that want the arrival's content words; stems are what select on."""
    return [w for w in WORD.findall(text.lower()) if w not in STOPWORDS and len(w) > 2]


def _contains(seq: Sequence[str], phrase: Sequence[str]) -> bool:
    n = len(phrase)
    if n == 0 or n > len(seq):
        return False
    return any(tuple(seq[i:i + n]) == tuple(phrase) for i in range(len(seq) - n + 1))


@dataclass
class Section:
    file: str
    heading: str
    text: str
    line: int
    level: int = 2
    heading_stems: Tuple[str, ...] = ()
    body_stems: Tuple[str, ...] = ()
    body_set: frozenset = frozenset()


@dataclass
class Term:
    phrase: str
    file: str
    stems: Tuple[str, ...]


@dataclass
class Passage:
    file: str
    heading: str
    text: str
    line: int
    score: float
    consequential: bool
    matched: List[str] = field(default_factory=list)
    terms: List[str] = field(default_factory=list)

    def as_record(self) -> Dict[str, Any]:
        return {"file": self.file, "heading": self.heading, "line": self.line, "score": self.score,
                "consequential": self.consequential, "matched": list(self.matched),
                "terms": list(self.terms), "text": self.text}


class Corpus:
    def __init__(self, directory: str) -> None:
        self.directory = os.path.abspath(directory)
        self.index_file: Optional[str] = None
        self.files: List[str] = []
        self.sections: List[Section] = []
        self.headers: Dict[str, str] = {}
        self.terms: List[Term] = []
        self.df: Dict[str, int] = {}
        self._load()

    # -- loading -----------------------------------------------------------

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
        self._index()

    def _split(self, name: str, path: str) -> None:
        with open(path, encoding="utf-8") as handle:
            lines = handle.read().splitlines()
        self.headers[name] = "\n".join(lines[:6]).strip()
        heading = os.path.splitext(name)[0]
        level = 1
        start = 0
        buffer: List[str] = []
        for i, line in enumerate(lines):
            m = HEADING.match(line)
            if m:
                text = "\n".join(buffer).strip()
                if text:
                    self.sections.append(Section(name, heading, text, start + 1, level))
                heading = m.group(2)
                level = len(m.group(1))
                start = i
                buffer = []
            else:
                buffer.append(line)
        text = "\n".join(buffer).strip()
        if text:
            self.sections.append(Section(name, heading, text, start + 1, level))

    def _index(self) -> None:
        for s in self.sections:
            s.heading_stems = tuple(stems(s.heading))
            s.body_stems = tuple(stems(s.text))
            s.body_set = frozenset(s.body_stems)
            for st in set(s.heading_stems) | s.body_set:
                self.df[st] = self.df.get(st, 0) + 1
        # The canon's own vocabulary: entry headings of the glossary files,
        # or of every active file when the corpus carries no glossary.
        glossaries = [f for f in self.files if "glossary" in f.lower()]
        seen = set()
        for s in self.sections:
            if s.level < 2 or (glossaries and s.file not in glossaries):
                continue
            if "glossary" in s.heading.lower() or s.heading.lower().startswith("changes from"):
                continue
            for part in re.split(r",|\band\b|/", s.heading):
                part = part.strip()
                st = tuple(stems(part))
                if not st or st in seen:
                    continue
                seen.add(st)
                self.terms.append(Term(part, s.file, st))

    def idf(self, st: str) -> float:
        n = len(self.sections) or 1
        return math.log(n / (1 + self.df.get(st, 0)))

    def describe(self) -> Dict[str, Any]:
        return {"directory": self.directory, "index": self.index_file, "files": list(self.files),
                "sections": len(self.sections), "terms": len(self.terms)}

    # -- selection ---------------------------------------------------------

    def matches(self, text: str) -> List[Tuple[Term, bool]]:
        """The canon terms an arrival names, longest phrases first.

        Each item is ``(term, partial)``. A full match is the whole phrase. A
        partial match is a bare head word ("a cut" for ``Agential Cut``),
        allowed only when that head belongs to exactly one multi-word term and
        is not a term by itself; it ranks the entry but does not mark it
        consequential, since the arrival did not name it.
        """
        q = stems(text)
        found = [t for t in self.terms if _contains(q, t.stems)]
        found.sort(key=lambda t: -len(t.stems))
        # A shorter term wholly inside a longer matched one is not named on
        # its own ("Creative Becoming" inside "Intra-active Creative Becoming").
        kept: List[Tuple[Term, bool]] = []
        for t in found:
            if any(len(k.stems) > len(t.stems) and _contains(k.stems, t.stems) for k, _ in kept):
                continue
            kept.append((t, False))
        covered = set(st for t, _ in kept for st in t.stems)
        singles = set(t.stems for t in self.terms if len(t.stems) == 1)
        heads: Dict[str, int] = {}
        for t in self.terms:
            if len(t.stems) >= 2:
                heads[t.stems[-1]] = heads.get(t.stems[-1], 0) + 1
        for t in self.terms:
            if len(t.stems) < 2:
                continue
            head = t.stems[-1]
            if heads[head] == 1 and (head,) not in singles and head in q and head not in covered:
                kept.append((t, True))
        return kept

    def terms_in(self, text: str) -> List[Term]:
        """The canon terms an arrival names as whole phrases."""
        return [t for t, partial in self.matches(text) if not partial]

    def select(self, query: str, limit: int = 4) -> List[Passage]:
        q = stems(query)
        if not q:
            return []
        named = self.matches(query)
        term_stems = set(st for t, partial in named for st in (t.stems if not partial else (t.stems[-1],)))
        loose = [st for st in dict.fromkeys(q) if st not in term_stems]
        scored: List[Passage] = []
        for s in self.sections:
            if s.heading.lower().startswith("changes from"):
                continue  # version history, not canon content
            score = 0.0
            matched: List[str] = []
            terms: List[str] = []
            consequential = False
            for t, partial in named:
                if partial:
                    if s.level >= 2 and tuple(s.heading_stems) == t.stems:
                        score += TERM_HEADING / 2
                        terms.append("%s (head word only)" % t.phrase)
                    continue
                if s.level >= 2 and tuple(s.heading_stems) == t.stems:
                    score += TERM_HEADING
                    consequential = True
                    terms.append(t.phrase)
                elif s.level >= 2 and _contains(s.heading_stems, t.stems):
                    score += TERM_HEADING / 2
                    terms.append(t.phrase)
                elif _contains(s.body_stems, t.stems):
                    score += TERM_BODY
                    terms.append(t.phrase)
            for st in loose:
                w = self.idf(st)
                if w <= 0:
                    continue
                if s.level >= 2 and st in s.heading_stems:
                    score += 2 * w
                    matched.append(st)
                elif st in s.body_set:
                    score += w
                    matched.append(st)
            if terms or (len(matched) >= 2 and score >= FLOOR):
                scored.append(Passage(s.file, s.heading, s.text, s.line, round(score, 2),
                                      consequential, matched, terms))
        scored.sort(key=lambda p: (not p.consequential, -p.score, self.files.index(p.file), p.line))
        return scored[:limit]
