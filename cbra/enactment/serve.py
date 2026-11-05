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
    uvicorn.run(create_app(store_dir=args.store_dir, model=args.model, max_rounds=args.max_rounds),
                host=args.host, port=args.port, log_level="info")
    return 0


if __name__ == "__main__":
    sys.exit(main())
