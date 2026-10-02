# SPDX-License-Identifier: MIT
# Copyright (c) 2026 John Luke NIKABOU (LucNIK)

"""Command line entry point: `python -m profile_engine --config profile.toml --out dist`."""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

from . import __version__
from .config import load
from .context import build
from .modules import REGISTRY, game


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="profile-engine", description=__doc__)
    parser.add_argument("--config", default="profile.toml", help="path to profile.toml")
    parser.add_argument("--out", default="dist", help="output directory for the SVGs")
    parser.add_argument("--modules", default="all",
                        help=f"comma-separated subset of: {', '.join(REGISTRY)} (default: all)")
    parser.add_argument("--offline", action="store_true",
                        help="no network: use cached or sample data (for previews and tests)")
    parser.add_argument("--game-move", default=os.environ.get("ENGINE_GAME_MOVE", ""),
                        help="issue title of a Connect Four move, e.g. 'connect4|drop|4'")
    parser.add_argument("--game-player", default=os.environ.get("ENGINE_GAME_PLAYER", ""),
                        help="GitHub login of the player making the move")
    parser.add_argument("--game-process-issues", action="store_true",
                        default=os.environ.get("ENGINE_GAME_PROCESS_ISSUES", "").lower() == "true",
                        help="play every open 'connect4|drop|N' issue, reply to it and close it")
    parser.add_argument("--game-reply", default="game-reply.md",
                        help="where to write the markdown reply for the issue")
    parser.add_argument("--version", action="version", version=f"profile-engine {__version__}")
    args = parser.parse_args(argv)

    names = list(REGISTRY) if args.modules == "all" else [m.strip() for m in args.modules.split(",") if m.strip()]
    unknown = [n for n in names if n not in REGISTRY]
    if unknown:
        parser.error(f"unknown module(s): {', '.join(unknown)}")

    ctx = build(load(args.config), Path(args.out), offline=args.offline)
    if args.game_move:
        reply = game.play(ctx, args.game_move, args.game_player or "someone")
        Path(args.game_reply).write_text(reply, encoding="utf-8")
        print(f"[engine] game      {reply.splitlines()[0][:100]}")
    if args.game_process_issues and not args.offline:
        try:
            print(f"[engine] game      {game.process_issues(ctx)} move issue(s) processed")
        except Exception as exc:  # never block the render because the issue queue failed
            print(f"[engine] game      issue queue FAIL {exc!r}", file=sys.stderr)
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
