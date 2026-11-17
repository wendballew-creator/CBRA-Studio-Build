"""Minimal public interface: a line-oriented loop over the runtime.

    python -m cbra.enactment [--store PATH] [--model NAME]

Lines are turns. ``/effect <text>`` reports an observed effect and asks the
proposer which active conditions it meets; ``/effect! cond1,cond2 <text>``
names them directly. ``/trace`` prints the configuration trace summary,
``/self`` the runtime's account of which parts enact and which record,
``/quit`` exits. Lifecycle facts are printed as they occur; they are the only
statuses the runtime reports.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

from .persistence import JsonStore
from .proposer import OpenAIResponsesProposer
from .runtime import Runtime


def _load_env() -> None:
    try:
        from dotenv import load_dotenv  # type: ignore
        load_dotenv(os.path.join(os.getcwd(), ".env"))
    except Exception:
        pass


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="cbra.enactment")
    parser.add_argument("--store", default=os.path.join(".cbra-runtime", "enactment.json"))
    parser.add_argument("--model", default=None)
    args = parser.parse_args(argv)
    _load_env()
    if not os.environ.get("OPENAI_API_KEY"):
        print("No OPENAI_API_KEY in the environment; the proposer cannot be started.", file=sys.stderr)
        return 2
    runtime = Runtime(OpenAIResponsesProposer(model=args.model), store=JsonStore(args.store))
    print("cbra.enactment: configuration version %d, %d cuts. /trace /self /effect /quit" % (
        runtime.config.version, len(runtime.config.cuts)))
    for line in sys.stdin:
        line = line.rstrip("\n")
        if not line.strip():
            continue
        if line.strip() == "/quit":
            break
        if line.strip() == "/trace":
            t = runtime.config.trace()
            print(json.dumps({k: (len(v) if isinstance(v, list) else v) for k, v in t.items() if k != "records"}, indent=1))
            continue
        if line.strip() == "/self":
            print(json.dumps(runtime.account_of_self(), indent=1))
            continue
        if line.startswith("/effect! "):
            rest = line[len("/effect! "):]
            conds, _, text = rest.partition(" ")
            result = runtime.effect(text, conditions=[c for c in conds.split(",") if c])
        elif line.startswith("/effect "):
            result = runtime.effect(line[len("/effect "):])
        else:
            result = runtime.turn(line)
            for fact in result.facts:
                print("[%s]" % fact["fact"], {k: v for k, v in fact.items() if k not in ("fact", "timestamp", "version")})
            if result.released:
                print(result.text)
            else:
                print("(release withheld; deferral %s enacted; constraints: %s)" % (result.intervention, ", ".join(
                    "%d" % v.constraint for v in result.violations[-1])))
            continue
        print(json.dumps({k: v for k, v in result.as_record().items() if k != "deltas"}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
