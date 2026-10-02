"""Command line entry point: `python -m profile_engine --config profile.toml --out dist`."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from . import __version__
from .config import load
from .context import build
from .modules import REGISTRY


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="profile-engine", description=__doc__)
    parser.add_argument("--config", default="profile.toml", help="path to profile.toml")
    parser.add_argument("--out", default="dist", help="output directory for the SVGs")
    parser.add_argument("--modules", default="all",
                        help=f"comma-separated subset of: {', '.join(REGISTRY)} (default: all)")
    parser.add_argument("--offline", action="store_true",
                        help="no network: use cached or sample data (for previews and tests)")
    parser.add_argument("--version", action="version", version=f"profile-engine {__version__}")
    args = parser.parse_args(argv)

    names = list(REGISTRY) if args.modules == "all" else [m.strip() for m in args.modules.split(",") if m.strip()]
    unknown = [n for n in names if n not in REGISTRY]
    if unknown:
        parser.error(f"unknown module(s): {', '.join(unknown)}")

    ctx = build(load(args.config), Path(args.out), offline=args.offline)
    failures = 0
    for name in names:
        started = time.perf_counter()
        try:
            REGISTRY[name](ctx)
            print(f"[engine] {name:<9} ok   {time.perf_counter() - started:5.2f}s")
        except Exception as exc:  # one broken module must never take the whole profile down
            failures += 1
            print(f"[engine] {name:<9} FAIL {exc!r}", file=sys.stderr)
    ctx.save_state()
    # Fail the run only if everything failed — partial output is still worth publishing.
    return 1 if failures == len(names) else 0


if __name__ == "__main__":
    sys.exit(main())
