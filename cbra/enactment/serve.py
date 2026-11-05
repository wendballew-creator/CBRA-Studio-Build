"""Serve the enactment slice's test page.

    python -m cbra.enactment.serve [--host 127.0.0.1] [--port 8765] [--model NAME]

Loads .env from the working directory for the provider key. The key stays on
the server; the page never sees it.
"""

from __future__ import annotations

import argparse
import os
import sys


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="cbra.enactment.serve")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--model", default=None)
    parser.add_argument("--store-dir", default=os.path.join(".cbra-runtime", "sessions"))
    parser.add_argument("--max-rounds", type=int, default=3)
    parser.add_argument("--corpus-dir", default=os.environ.get("CBRA_CORPUS_DIR") or ("corpus" if os.path.isdir("corpus") else None),
                        help="directory holding the canon files and their corpus index (default: $CBRA_CORPUS_DIR or ./corpus)")
    args = parser.parse_args(argv)
    try:
        from dotenv import load_dotenv  # type: ignore
        load_dotenv(os.path.join(os.getcwd(), ".env"))
    except Exception:
        pass
    if not os.environ.get("OPENAI_API_KEY"):
        print("Warning: no OPENAI_API_KEY; the page will load but turns will fail with 503.", file=sys.stderr)
    import uvicorn
    from .api import create_app
    if args.corpus_dir:
        print("Canon material from %s" % os.path.abspath(args.corpus_dir), file=sys.stderr)
    else:
        print("Warning: no corpus directory; the proposer will see no canon material.", file=sys.stderr)
    uvicorn.run(create_app(store_dir=args.store_dir, model=args.model, max_rounds=args.max_rounds, corpus_dir=args.corpus_dir),
                host=args.host, port=args.port, log_level="info")
    return 0


if __name__ == "__main__":
    sys.exit(main())
