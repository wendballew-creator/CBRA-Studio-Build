"""The measurement run: a fixed set of probes through the runtime, and a
report that places the uninstructed baseline beside the released text.

    python -m cbra.enactment.measure run [--probes measurement/probes.md] [--out DIR]
    python -m cbra.enactment.measure report RUN_DIR [--corpus-dir DIR] [--out FILE]

Each probe opens a fresh session, so no probe sees another's cuts. The run
changes nothing about the method: the same ``Runtime`` the page uses forms
each turn, with the same canon, proposer and constraints. What the run adds
is a fixed set, a record of each turn's timing and outcome beside its
session file, and a document that reads the session files back into one
place: the baseline answer, the released text, the material drawn and how
it was marked, the cuts the release rested on, the returns with their
reasons, and the care and play deltas.

The report is a reading aid. It certifies nothing, and the comparison it
makes is between one model's constrained answer and the same model's
unconstrained one. Whether the cuts, rather than the instruction to use
canon material, made the difference is not something it can show.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence

from .graph import Configuration
from .material import Corpus
from .persistence import JsonStore
from .probes import code_version
from .proposer import Proposer
from .release import CONSTRAINT_NAMES
from .runtime import Runtime

PROBE_KEYS = ("targets", "prompt", "then")
WORD = re.compile(r"[a-z][a-z'-]{3,}")


# -- the probe set -----------------------------------------------------------

@dataclass
class Probe:
    id: str
    targets: str
    prompts: List[str]

    def as_record(self) -> Dict[str, Any]:
        return {"id": self.id, "targets": self.targets, "prompts": list(self.prompts)}


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.strip().lower()).strip("-") or "probe"


def load_probes(path: str) -> List[Probe]:
    """Read the probe set. A ``##`` heading begins a probe; ``Targets:``,
    ``Prompt:`` and ``Then:`` lines fill it; a line that starts with none of
    them continues the previous one. Text before the first heading is
    ignored, so the file can explain itself."""
    probes: List[Probe] = []
    current: Optional[Dict[str, Any]] = None
    key: Optional[str] = None
    with open(path, encoding="utf-8") as handle:
        for raw in handle:
            line = raw.rstrip("\n")
            if line.startswith("## "):
                if current is not None:
                    probes.append(_finish(current, path))
                current = {"id": _slug(line[3:]), "targets": "", "prompt": "", "then": []}
                key = None
                continue
            if current is None or not line.strip():
                key = None if not line.strip() else key
                continue
            lowered = line.lower()
            matched = next((k for k in PROBE_KEYS if lowered.startswith(k + ":")), None)
            if matched:
                key = matched
                value = line.split(":", 1)[1].strip()
                if key == "then":
                    current["then"].append(value)
                else:
                    current[key] = value
            elif key == "then":
                current["then"][-1] = (current["then"][-1] + " " + line.strip()).strip()
            elif key:
                current[key] = (current[key] + " " + line.strip()).strip()
    if current is not None:
        probes.append(_finish(current, path))
    ids = [p.id for p in probes]
    duplicates = sorted({i for i in ids if ids.count(i) > 1})
    if duplicates:
        raise ValueError("%s: probe ids repeat: %s" % (path, ", ".join(duplicates)))
    return probes


def _finish(current: Dict[str, Any], path: str) -> Probe:
    if not current["prompt"]:
        raise ValueError("%s: probe %r has no Prompt line" % (path, current["id"]))
    return Probe(current["id"], current["targets"], [current["prompt"]] + list(current["then"]))


# -- the run -----------------------------------------------------------------

@dataclass
class TurnRun:
    prompt: str
    turn: Optional[str] = None
    released: Optional[bool] = None
    form: Optional[str] = None
    rounds: Optional[int] = None
    intervention: Optional[str] = None
    seconds: float = 0.0
    error: Optional[str] = None

    def as_record(self) -> Dict[str, Any]:
        return dict(self.__dict__)


@dataclass
class ProbeRun:
    probe: Probe
    session_path: str
    turns: List[TurnRun] = field(default_factory=list)

    def as_record(self) -> Dict[str, Any]:
        return {"probe": self.probe.as_record(), "session_path": self.session_path,
                "turns": [t.as_record() for t in self.turns]}


def run(probes: Sequence[Probe], proposer: Proposer, out_dir: str, material: Optional[Corpus] = None,
        max_rounds: int = 3, observer: Any = None, clock: Any = time) -> Dict[str, Any]:
    """Send each probe's prompts through a fresh runtime and write
    ``run.json`` beside the session files. The manifest is rewritten after
    every probe, so a run that stops early still leaves a record of what it
    finished. A provider failure on one probe is recorded against that probe
    and the run goes on to the next."""
    sessions_dir = os.path.join(out_dir, "sessions")
    os.makedirs(sessions_dir, exist_ok=True)
    manifest: Dict[str, Any] = {
        "started": datetime.now().isoformat(timespec="seconds"),
        "finished": None,
        "code_version": code_version(),
        "model": getattr(proposer, "model", type(proposer).__name__),
        "canon": material.describe() if material is not None else None,
        "max_rounds": max_rounds,
        "probes": [],
    }
    runs: List[ProbeRun] = []
    for probe in probes:
        path = os.path.join(sessions_dir, probe.id + ".json")
        if os.path.exists(path):
            os.remove(path)
        store = JsonStore(path)
        runtime = Runtime(proposer, store=store, max_rounds=max_rounds, channel="measurement",
                          observer=observer, material=material)
        runtime.config.session = probe.id
        probe_run = ProbeRun(probe, path)
        runs.append(probe_run)
        for prompt in probe.prompts:
            record = TurnRun(prompt=prompt)
            probe_run.turns.append(record)
            started = clock.time()
            try:
                result = runtime.turn(prompt)
            except Exception as error:  # the runtime saved what it formed; the run records the failure and goes on
                record.seconds = round(clock.time() - started, 1)
                record.error = "%s: %s" % (type(error).__name__, error)
                if observer is not None:
                    observer({"event": "error", "probe": probe.id, "error": record.error})
                break
            record.seconds = round(clock.time() - started, 1)
            record.turn, record.released, record.form = result.turn, result.released, result.form
            record.rounds, record.intervention = result.rounds, result.intervention
            if observer is not None:
                observer({"event": "probe_turn", "probe": probe.id, "turn": result.turn, "released": result.released,
                          "form": result.form, "rounds": result.rounds, "seconds": record.seconds})
        manifest["probes"] = [r.as_record() for r in runs]
        _write_manifest(out_dir, manifest)
    manifest["finished"] = datetime.now().isoformat(timespec="seconds")
    _write_manifest(out_dir, manifest)
    return manifest


def _write_manifest(out_dir: str, manifest: Dict[str, Any]) -> None:
    path = os.path.join(out_dir, "run.json")
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=1, ensure_ascii=False)
    os.replace(tmp, path)


# -- reading a session back -----------------------------------------------------

def _cut_number(cut_id: str) -> int:
    digits = re.sub(r"\D", "", cut_id)
    return int(digits) if digits else 0


def turn_reading(config: Configuration, turn: str, corpus: Optional[Corpus] = None) -> Dict[str, Any]:
    """Everything the report says about one turn, read from the
    configuration: the arrival, the uninstructed baseline, the release or
    deferral, the material and how it was marked, the cuts the release
    rested on, the returns, and the derived deltas as the release recorded
    them."""
    arrival = next((f for f in config.lifecycle if f.get("fact") == "reconfiguration_open" and f.get("turn") == turn), None)
    arrival_text = config.transports[arrival["arrival"]].text if arrival and arrival.get("arrival") in config.transports else None
    baseline = [c for c in config.cuts.values()
                if c.kind == "arrangement" and c.payload.get("role") == "baseline" and c.payload.get("turn") == turn]
    interventions = sorted((c for c in config.cuts.values() if c.kind == "intervention" and c.payload.get("turn") == turn),
                           key=lambda c: _cut_number(c.id))
    intervention = interventions[-1] if interventions else None
    payload = intervention.payload if intervention is not None else {}
    returns = []
    for c in config.cuts.values():
        if c.kind == "apparatus" and c.label.startswith("release_constraints_fired:%s:r" % turn):
            returns.append({"round": int(c.label.rsplit(":r", 1)[-1]), "constraints": list(c.payload.get("violations", []))})
    returns.sort(key=lambda r: r["round"])
    material = []
    for h in payload.get("material", []):
        t = config.transports.get(h)
        if t is None:
            continue
        p = t.provenance
        material.append({"handle": h, "file": p.get("file"), "heading": p.get("heading"), "via": p.get("via") or "terms",
                         "consequential": bool(p.get("consequential")), "terms": list(p.get("terms") or []),
                         "drawn_by": p.get("drawn_by"), "similarity": p.get("similarity")})
    rested_on = []
    if intervention is not None:
        for cid in intervention.depends_on:
            c = config.cuts.get(cid)
            if c is not None:
                rested_on.append({"id": c.id, "kind": c.kind, "label": c.label, "relata": list(c.relata),
                                  "material": [h for h in c.basis if h in config.transports and config.transports[h].role == "document"]})
    released = payload.get("text") if intervention is not None and payload.get("form") != "deferral" else None
    baseline_text = baseline[-1].payload.get("source_text") if baseline else None
    reading = {
        "turn": turn,
        "arrival": arrival_text,
        "baseline_text": baseline_text,
        "baseline_unavailable": any(u.get("kind") == "baseline_unavailable" and u.get("turn") == turn for u in config.unresolved),
        "form": payload.get("form"),
        "released_text": released,
        "rounds": payload.get("rounds"),
        "claims": list(payload.get("claims") or []),
        "withheld_constraints": list(payload.get("withheld_constraints") or []),
        "returns": returns,
        "material": material,
        "material_required": list(payload.get("material_required") or []),
        "rested_on": rested_on,
        "care_delta": sorted((payload.get("care_delta") or {}).keys()),
        "play_delta": {k: sorted(v.keys()) for k, v in (payload.get("play_delta") or {}).items()},
        "text_unread": any(u.get("kind") == "text_unread" and u.get("turn") == turn for u in config.unresolved),
        "canon_terms": {"baseline": _terms(corpus, baseline_text), "released": _terms(corpus, released)},
        "shared_vocabulary": _shared(baseline_text, released),
        "words": {"baseline": len(WORD.findall((baseline_text or "").lower())), "released": len(WORD.findall((released or "").lower()))},
    }
    return reading


def _terms(corpus: Optional[Corpus], text: Optional[str]) -> List[str]:
    if corpus is None or not text:
        return []
    seen: List[str] = []
    for term in corpus.terms_in(text):
        if term.phrase not in seen:
            seen.append(term.phrase)
    return seen


def _shared(a: Optional[str], b: Optional[str]) -> Optional[float]:
    """The share of the released text's distinct words that also occur in
    the baseline. A crude figure; it says how much of the wording survived,
    not whether the structure did."""
    if not a or not b:
        return None
    wa, wb = set(WORD.findall(a.lower())), set(WORD.findall(b.lower()))
    if not wb:
        return None
    return round(len(wa & wb) / len(wb), 2)


def turns_of(config: Configuration) -> List[str]:
    seen: List[str] = []
    for f in config.lifecycle:
        if f.get("fact") == "reconfiguration_open" and f.get("turn") not in seen:
            seen.append(f["turn"])
    return seen


# -- the report ----------------------------------------------------------------

def _cell(text: Optional[str]) -> str:
    if not text:
        return "—"
    return text.replace("|", "\\|").replace("\r", "").replace("\n", "<br>")


def _short(text: str, limit: int = 60) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def _outcome(turn: TurnRun, reading: Dict[str, Any]) -> str:
    if turn.error:
        return "error"
    if not turn.released:
        return "withheld after %s rounds" % (turn.rounds if turn.rounds is not None else "?")
    return "released r%s%s" % (turn.rounds, " (minimal)" if turn.form == "minimal" else "")


def _returns_cell(reading: Dict[str, Any]) -> str:
    parts = ["r%d: %s" % (r["round"], ", ".join(str(v.get("constraint")) for v in r["constraints"]) or "—")
             for r in reading["returns"]]
    if reading["withheld_constraints"]:
        parts.append("withheld: %s" % ", ".join(str(v.get("constraint")) for v in reading["withheld_constraints"]))
    return "; ".join(parts) if parts else "none"


def _cut_drawn(m: Dict[str, Any]) -> bool:
    """Drawn by the live cuts of a returned round, not by the arrival."""
    return bool(m.get("drawn_by")) and m["drawn_by"] != "the arrival"


def _material_cell(reading: Dict[str, Any]) -> str:
    m = reading["material"]
    if not m:
        return "none"
    named = sum(1 for x in m if x["consequential"])
    drawn = sum(1 for x in m if not x["consequential"] and _cut_drawn(x))
    similar = sum(1 for x in m if not x["consequential"] and not _cut_drawn(x) and x["via"] == "similarity")
    other = len(m) - named - drawn - similar
    parts = []
    if named:
        parts.append("%d named" % named)
    if similar:
        parts.append("%d similar" % similar)
    if drawn:
        parts.append("%d drawn by cuts" % drawn)
    if other:
        parts.append("%d by words" % other)
    return ", ".join(parts)


def _terms_cell(reading: Dict[str, Any]) -> str:
    b, r = reading["canon_terms"]["baseline"], reading["canon_terms"]["released"]
    return "%d → %d" % (len(b), len(r))


def report(run_dir: str, corpus: Optional[Corpus] = None) -> str:
    """Read ``run.json`` and the session files under ``run_dir`` into one
    Markdown document."""
    with open(os.path.join(run_dir, "run.json"), encoding="utf-8") as handle:
        manifest = json.load(handle)
    canon = manifest.get("canon") or {}
    lines: List[str] = []
    lines.append("# Measurement run, %s" % manifest["started"][:10])
    lines.append("")
    lines.append("Started %s, finished %s. Code `%s`. Model `%s`. Canon: %s (%s active files, %s sections, %s terms)%s. "
                 "Up to %s formed rounds and one minimal round per turn. Each probe ran in a fresh session." % (
                     manifest["started"].replace("T", " "), (manifest.get("finished") or "not finished").replace("T", " "),
                     manifest["code_version"], manifest["model"], canon.get("index") or "none",
                     len(canon.get("files") or []), canon.get("sections", 0), canon.get("terms", 0),
                     ", similarity pass with `%s`" % canon["embedding_model"] if canon.get("embedding_model") else "",
                     manifest["max_rounds"]))
    lines.append("")
    lines.append("The left column of each comparison is what the model said to the same arrival with no CBRA instructions; "
                 "the right column is what the method released. The material, the cuts the release rested on, the returns "
                 "and the deltas are read from the session files, not restated by anyone. \"Canon terms\" counts glossary "
                 "terms named as whole phrases in each text. \"Shared vocabulary\" is the share of the released text's "
                 "distinct words that also occur in the baseline; it measures wording, not structure.")
    lines.append("")
    readings: List[Dict[str, Any]] = []
    for pr in manifest["probes"]:
        probe = pr["probe"]
        config = None
        if os.path.exists(pr["session_path"]):
            config = JsonStore(pr["session_path"]).load(session=probe["id"])
        turns = turns_of(config) if config is not None else []
        per_turn = []
        for index, turn_record in enumerate(pr["turns"]):
            t = TurnRun(**turn_record)
            reading = turn_reading(config, turns[index], corpus) if config is not None and index < len(turns) else {
                "turn": None, "arrival": t.prompt, "baseline_text": None, "baseline_unavailable": False, "form": None,
                "released_text": None, "rounds": None, "claims": [], "withheld_constraints": [], "returns": [],
                "material": [], "material_required": [], "rested_on": [], "care_delta": [], "play_delta": {},
                "text_unread": False, "canon_terms": {"baseline": [], "released": []}, "shared_vocabulary": None,
                "words": {"baseline": 0, "released": 0}}
            per_turn.append((t, reading))
        readings.append({"probe": probe, "turns": per_turn})

    lines.append("## Summary")
    lines.append("")
    lines.append("| Probe | Turn | Outcome | Returns | Material | Care delta | Canon terms | Shared words | Seconds |")
    lines.append("|---|---|---|---|---|---|---|---|---|")
    for item in readings:
        for t, reading in item["turns"]:
            care = ", ".join(reading["care_delta"]) if reading["care_delta"] else ("claimed, none" if "care" in reading["claims"] else "—")
            shared = "%.2f" % reading["shared_vocabulary"] if reading["shared_vocabulary"] is not None else "—"
            lines.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
                item["probe"]["id"], reading["turn"] or "—", _outcome(t, reading), _returns_cell(reading),
                _material_cell(reading), _cell(care), _terms_cell(reading), shared, "%.0f" % t.seconds))
    lines.append("")

    for item in readings:
        probe = item["probe"]
        lines.append("## %s" % probe["id"])
        lines.append("")
        if probe.get("targets"):
            lines.append("**Targets.** %s" % probe["targets"])
            lines.append("")
        for t, reading in item["turns"]:
            lines.append("### %s — “%s”" % (reading["turn"] or "turn", _short(t.prompt, 90)))
            lines.append("")
            if t.error:
                lines.append("The turn failed after %.0f s: `%s`. What the runtime formed before the failure is in the session file." % (t.seconds, t.error))
                lines.append("")
                continue
            if t.released:
                lines.append("Released on round %s%s after %.0f s." % (
                    t.rounds, " under minimal terms" if t.form == "minimal" else "", t.seconds))
            else:
                lines.append("Release withheld after %s rounds; a deferral was enacted (%.0f s)." % (t.rounds, t.seconds))
            if reading["baseline_unavailable"]:
                lines.append("The uninstructed baseline could not be obtained for this turn.")
            lines.append("")
            lines.append("| Uninstructed answer | Released text |")
            lines.append("|---|---|")
            lines.append("| %s | %s |" % (_cell(reading["baseline_text"]), _cell(reading["released_text"]) if t.released else "*(withheld)*"))
            lines.append("")
            if reading["material"]:
                lines.append("**Material drawn.**")
                lines.append("")
                for m in reading["material"]:
                    mark = []
                    if m["consequential"]:
                        mark.append("named: %s" % ", ".join(m["terms"]) if m["terms"] else "named")
                    elif _cut_drawn(m):
                        mark.append("drawn by %s" % m["drawn_by"])
                    elif m["via"] == "similarity":
                        mark.append("similar%s" % (", %.2f" % m["similarity"] if m["similarity"] is not None else ""))
                    else:
                        mark.append("by words")
                    grounded = any(m["handle"] in c["material"] for c in reading["rested_on"])
                    lines.append("- %s › %s (%s)%s" % (m["file"], m["heading"], "; ".join(mark), "; a cut the release rests on draws on it" if grounded else ""))
                lines.append("")
            else:
                lines.append("**Material drawn.** None.")
                lines.append("")
            if reading["rested_on"]:
                lines.append("**Cuts the release rested on.**")
                lines.append("")
                for c in reading["rested_on"]:
                    relata = "; relata: %s" % ", ".join(c["relata"]) if c["relata"] else ""
                    lines.append("- %s `%s`%s" % (c["kind"], c["label"], relata))
                lines.append("")
            if reading["returns"]:
                lines.append("**Returned drafts.**")
                lines.append("")
                for r in reading["returns"]:
                    for v in r["constraints"]:
                        number = v.get("constraint")
                        lines.append("- Round %d, constraint %s (%s): %s" % (
                            r["round"], number, CONSTRAINT_NAMES.get(int(number), v.get("name", "")) if str(number).isdigit() else v.get("name", ""),
                            v.get("reason", "")))
                lines.append("")
            elif t.released:
                lines.append("**Returned drafts.** None; the first draft released.")
                lines.append("")
            if reading["withheld_constraints"]:
                lines.append("**Withheld on.**")
                lines.append("")
                for v in reading["withheld_constraints"]:
                    lines.append("- Constraint %s: %s" % (v.get("constraint"), v.get("reason", "")))
                lines.append("")
            if "care" in reading["claims"]:
                lines.append("**Care delta.** %s" % (
                    "baseline and enacted arrangements differ on: %s." % ", ".join(reading["care_delta"]) if reading["care_delta"]
                    else "care was claimed and no structural difference from the baseline was found."))
            else:
                lines.append("**Care delta.** No care claim on this release.")
            if reading["play_delta"]:
                lines.append("**Play delta.** %s" % "; ".join(
                    "alternative %s varies: %s" % (k, ", ".join(v)) for k, v in reading["play_delta"].items()))
            else:
                lines.append("**Play delta.** No alternative arrangement with material variation.")
            if reading["text_unread"]:
                lines.append("**Text reading.** The released text was not read back against its arrangement (no reading apparatus).")
            if corpus is not None:
                b, r = reading["canon_terms"]["baseline"], reading["canon_terms"]["released"]
                lines.append("**Canon terms named.** Baseline: %s. Released: %s." % (", ".join(b) or "none", ", ".join(r) or "none"))
            if reading["shared_vocabulary"] is not None:
                lines.append("**Shared vocabulary.** %.2f of the released text's distinct words occur in the baseline (%d and %d words)." % (
                    reading["shared_vocabulary"], reading["words"]["baseline"], reading["words"]["released"]))
            lines.append("")
    lines.append("## Claim boundary")
    lines.append("")
    lines.append("The comparison is between one model's constrained and unconstrained answers to the same arrivals, on one run. "
                 "It does not show that the cuts, rather than the instruction to use canon material, made any difference seen here. "
                 "Nothing in this document establishes that CBRA is posthuman, that care was completed, or that Creative Becoming was achieved.")
    lines.append("")
    return "\n".join(lines)


# -- command line ------------------------------------------------------------------

def _load_env() -> None:
    try:
        from dotenv import load_dotenv  # type: ignore
        load_dotenv(os.path.join(os.getcwd(), ".env"))
    except Exception:
        pass


def _progress(event: Dict[str, Any]) -> None:
    kind = event.get("event")
    if kind == "probe_turn":
        print("  %s %s: %s on round %s (%s) in %.0f s" % (
            event["probe"], event["turn"], "released" if event["released"] else "withheld", event["rounds"],
            event["form"], event["seconds"]), file=sys.stderr, flush=True)
    elif kind == "error":
        print("  %s: %s" % (event.get("probe", "turn"), event.get("error")), file=sys.stderr, flush=True)
    elif kind in ("baseline", "round", "material"):
        print("    %s %s" % (kind, {k: v for k, v in event.items() if k not in ("event",)}), file=sys.stderr, flush=True)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="cbra.enactment.measure")
    sub = parser.add_subparsers(dest="command", required=True)
    r = sub.add_parser("run", help="send the probe set through the runtime and write a report")
    r.add_argument("--probes", default=os.path.join("measurement", "probes.md"))
    r.add_argument("--out", default=os.path.join(".cbra-runtime", "measurement"),
                   help="directory that receives one dated run directory per run")
    r.add_argument("--model", default=None)
    r.add_argument("--max-rounds", type=int, default=3)
    r.add_argument("--corpus-dir", default=os.environ.get("CBRA_CORPUS_DIR") or ("corpus" if os.path.isdir("corpus") else None))
    r.add_argument("--embedding-model", default=os.environ.get("CBRA_EMBEDDING_MODEL", "text-embedding-3-small"))
    r.add_argument("--embedding-cache", default=os.path.join(".cbra-runtime", "embeddings"))
    r.add_argument("--report", default=None, help="also write the report to this path")
    p = sub.add_parser("report", help="write the report for a finished run")
    p.add_argument("run_dir")
    p.add_argument("--corpus-dir", default=os.environ.get("CBRA_CORPUS_DIR") or ("corpus" if os.path.isdir("corpus") else None))
    p.add_argument("--out", default=None)
    args = parser.parse_args(argv)

    if args.command == "report":
        corpus = Corpus(args.corpus_dir) if args.corpus_dir else None
        text = report(args.run_dir, corpus)
        out = args.out or os.path.join(args.run_dir, "report.md")
        with open(out, "w", encoding="utf-8") as handle:
            handle.write(text)
        print(out)
        return 0

    _load_env()
    if not os.environ.get("OPENAI_API_KEY"):
        print("No OPENAI_API_KEY in the environment; the proposer cannot be started.", file=sys.stderr)
        return 2
    from .proposer import OpenAIResponsesProposer
    probes = load_probes(args.probes)
    embedder = None
    if args.corpus_dir and args.embedding_model.lower() != "none":
        from .material import OpenAIEmbedder
        embedder = OpenAIEmbedder(model=args.embedding_model)
    corpus = Corpus(args.corpus_dir, embedder=embedder, cache_dir=args.embedding_cache) if args.corpus_dir else None
    run_dir = os.path.join(args.out, datetime.now().strftime("%Y-%m-%dT%H%M"))
    os.makedirs(run_dir, exist_ok=True)
    print("Measurement run: %d probes, %d arrivals, canon %s, into %s" % (
        len(probes), sum(len(p.prompts) for p in probes), (corpus.describe().get("index") if corpus else "none"), run_dir), file=sys.stderr)
    manifest = run(probes, OpenAIResponsesProposer(model=args.model), run_dir, material=corpus,
                   max_rounds=args.max_rounds, observer=_progress)
    text = report(run_dir, corpus)
    with open(os.path.join(run_dir, "report.md"), "w", encoding="utf-8") as handle:
        handle.write(text)
    if args.report:
        os.makedirs(os.path.dirname(os.path.abspath(args.report)), exist_ok=True)
        with open(args.report, "w", encoding="utf-8") as handle:
            handle.write(text)
    done = sum(1 for p in manifest["probes"] for t in p["turns"] if t["error"] is None)
    print("Finished: %d turns formed, %d failed. Report: %s" % (
        done, sum(1 for p in manifest["probes"] for t in p["turns"] if t["error"]), args.report or os.path.join(run_dir, "report.md")),
        file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
