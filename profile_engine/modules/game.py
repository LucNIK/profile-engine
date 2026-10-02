# SPDX-License-Identifier: MIT
# Copyright (c) 2026 John Luke NIKABOU (LucNIK)

"""Connect Four played through GitHub issues.

A visitor clicks a column button in the README, which opens a pre-filled issue titled
`connect4|drop|<column>`. The game workflow calls `play()`, the engine answers with its own move,
the board is re-rendered, and the issue gets a reply and is closed.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from urllib.parse import quote

from .. import connect4 as c4
from ..context import Context
from ..github import GitHub
from ..net import FetchError
from ..icons import icon
from ..svg import card, document, text
from ..theme import Theme

WIDTH, HEIGHT = 840, 430
CELL, PAD = 50, 26
BOARD_X, BOARD_Y = PAD + 4, 74
PANEL_X = BOARD_X + c4.COLS * CELL + 40

LOGIN_PATTERN = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?$")
ISSUE_BODY = ("Just press **Create** — your move is in the title.\n\n"
              "The engine will reply in a few seconds and the board on the profile will update.")


# ------------------------------------------------------------------ state

def new_game(state: dict) -> dict:
    game = state.setdefault("connect4", {})
    game.update({
        "board": c4.empty_board(), "over": False, "result": None, "win_line": None,
        "last": None, "game_no": game.get("game_no", 0) + 1,
    })
    game.setdefault("stats", {"human": 0, "ai": 0, "draw": 0})
    game.setdefault("players", {})
    game.setdefault("history", [])
    return game


def get_game(state: dict) -> dict:
    game = state.get("connect4")
    return game if game and "board" in game else new_game(state)


def issue_link(repo: str, column: int) -> str:
    title = quote(f"connect4|drop|{column}", safe="")
    return f"https://github.com/{repo}/issues/new?title={title}&body={quote(ISSUE_BODY)}"


def play(ctx: Context, title: str, player: str) -> str:
    """Apply a visitor's move and the engine's reply. Returns the markdown reply for the issue."""
    profile = f"https://github.com/{ctx.config.game_repo.split('/')[0]}"
    if not LOGIN_PATTERN.match(player or ""):  # never echo untrusted text into the reply or the board
        player = "visitor"
    col = c4.parse_move(title)
    if col is None:
        return ("I couldn't read a move in this issue's title. Use one of the column buttons on "
                f"[the profile]({profile}) — the title should look like `connect4|drop|4`.")
    game = get_game(ctx.state)
    if game["over"]:
        game = new_game(ctx.state)
    board = game["board"]
    if len(board[col]) >= c4.ROWS:
        return (f"Column {col + 1} is full, @{player}. Pick another column on [the profile]({profile}) "
                "and try again.")

    now = datetime.now(timezone.utc).isoformat()
    board = c4.drop(board, col, c4.HUMAN)
    entry = {"player": player, "col": col + 1, "ai": None, "at": now, "game": game["game_no"]}
    game["players"][player] = game["players"].get(player, 0) + 1
    reply_tail = f"\n\nSee the board on [the profile]({profile})."

    if c4.winner(board) == c4.HUMAN:
        _finish(game, board, "human")
        message = (f"🏆 **You win, @{player}!** Your disc in column {col + 1} completed four in a row "
                   "and beat the engine. A new game starts with the next move.")
    elif c4.is_full(board):
        _finish(game, board, "draw")
        message = f"Board full — **it's a draw**, @{player}. A new game starts with the next move."
    else:
        reply = c4.best_move(board, depth=ctx.config.game_depth)
        board = c4.drop(board, reply, c4.AI)
        entry["ai"] = reply + 1
        if c4.winner(board) == c4.AI:
            _finish(game, board, "ai")
            message = (f"You played column {col + 1}, @{player} — and the engine answered in column "
                       f"{reply + 1} to connect four. **The engine wins this one.** A new game starts "
                       "with the next move.")
        elif c4.is_full(board):
            _finish(game, board, "draw")
            message = f"Board full after the engine's move — **it's a draw**, @{player}."
        else:
            game["board"] = board
            message = (f"Nice move, @{player}! You dropped a disc in column {col + 1} and the engine "
                       f"answered in column {reply + 1}. Your turn — anyone can play the next move.")
    game["last"] = entry
    game["history"] = ([entry] + game["history"])[:20]
    return message + reply_tail


def process_issues(ctx: Context) -> int:
    """Play every open move issue, oldest first, reply to it and close it. Returns moves processed.

    Handling the whole queue on every run means no move is lost when GitHub drops a pending run.
    """
    repo = ctx.config.game_repo
    gh = GitHub(ctx.token)
    handled = 0
    for issue in gh.open_issues(repo):
        title = issue.get("title") or ""
        if not title.lower().lstrip().startswith("connect4"):
            continue
        player = (issue.get("user") or {}).get("login", "")
        valid = c4.parse_move(title) is not None
        reply = play(ctx, title, player)
        try:
            gh.comment(repo, issue["number"], reply)
            gh.close(repo, issue["number"], "completed" if valid else "not_planned")
        except FetchError as exc:
            print(f"[game] issue #{issue['number']}: {exc}")
            continue
        handled += 1
    return handled


def _finish(game: dict, board, result: str) -> None:
    game["board"] = board
    game["over"] = True
    game["result"] = result
    game["win_line"] = c4.winning_line(board)
    game["stats"][result] += 1


# ------------------------------------------------------------------ render

def _status(game: dict) -> tuple[str, str]:
    if game["over"]:
        return {"human": ("VISITORS WIN", "Four in a row! Next move starts a new game."),
                "ai": ("ENGINE WINS", "Think you can beat it? Start a new game."),
                "draw": ("DRAW", "Board full. Next move starts a new game.")}[game["result"]]
    moves = sum(len(col) for col in game["board"])
    return ("YOUR MOVE", "Drop a disc: pick a column below." if moves == 0
            else "Anyone can play the next move.")


def render_board(ctx: Context, theme: Theme, game: dict) -> str:
    human_c, ai_c = theme.accent, theme.muted
    win = {tuple(x) for x in (game.get("win_line") or [])}
    last = game.get("last") or {}
    last_cells = set()
    for key, owner in (("col", c4.HUMAN), ("ai", c4.AI)):
        col = (last.get(key) or 0) - 1
        if col >= 0 and last.get("game") == game["game_no"]:
            column = game["board"][col]
            for row in range(len(column) - 1, -1, -1):
                if column[row] == owner:
                    last_cells.add((col, row))
                    break

    title, subtitle = _status(game)
    out = [
        card(1, 1, WIDTH - 2, HEIGHT - 2, theme, r=14),
        icon("spark", PAD, 22, 18, theme.accent),
        text(PAD + 26, 36, "CONNECT FOUR · VISITORS VS ENGINE", size=12, fill=theme.text, weight=600,
             spacing=2.5),
        text(WIDTH - PAD, 36, f"Game #{game['game_no']}", size=12, fill=theme.muted, anchor="end"),
        f'<path d="M{PAD} 54H{WIDTH - PAD}" stroke="{theme.grid}"/>',
        f'<rect x="{BOARD_X - 8}" y="{BOARD_Y - 8}" width="{c4.COLS * CELL + 16}" '
        f'height="{c4.ROWS * CELL + 16}" rx="12" fill="none" stroke="{theme.border}"/>',
    ]
    for col in range(c4.COLS):
        for row in range(c4.ROWS):
            cx = BOARD_X + col * CELL + CELL / 2
            cy = BOARD_Y + (c4.ROWS - 1 - row) * CELL + CELL / 2
            who = c4.cell(game["board"], col, row)
            if who == 0:
                out.append(f'<circle cx="{cx}" cy="{cy}" r="18" fill="{theme.grid}"/>')
                continue
            fill = human_c if who == c4.HUMAN else ai_c
            out.append(f'<circle cx="{cx}" cy="{cy}" r="18" fill="{fill}"/>')
            if (col, row) in win:
                out.append(f'<circle cx="{cx}" cy="{cy}" r="22" fill="none" stroke="{theme.text}" '
                           f'stroke-width="2"/>')
            elif (col, row) in last_cells:
                out.append(f'<circle cx="{cx}" cy="{cy}" r="6" fill="{theme.surface}" opacity=".85"/>')
    for col in range(c4.COLS):
        out.append(text(BOARD_X + col * CELL + CELL / 2, BOARD_Y + c4.ROWS * CELL + 28, str(col + 1),
                        size=12, fill=theme.muted, weight=600, anchor="middle", mono=True))

    # side panel
    x = PANEL_X
    stats = game["stats"]
    out += [
        text(x, 98, title, size=22, fill=theme.accent if not game["over"] or game["result"] == "human"
             else theme.text, weight=600, spacing=1.5),
        text(x, 122, subtitle, size=13, fill=theme.muted),
        f'<circle cx="{x + 7}" cy="{151}" r="7" fill="{human_c}"/>',
        text(x + 22, 156, "Visitors", size=13, fill=theme.text),
        f'<circle cx="{x + 107}" cy="{151}" r="7" fill="{ai_c}"/>',
        text(x + 122, 156, "Engine (minimax AI)", size=13, fill=theme.text),
        f'<path d="M{x} 178H{WIDTH - PAD}" stroke="{theme.grid}"/>',
        text(x, 204, "SCORE", size=11, fill=theme.muted, weight=600, spacing=2),
    ]
    for i, (label, value) in enumerate((("Visitors", stats["human"]), ("Engine", stats["ai"]),
                                        ("Draws", stats["draw"]))):
        sx = x + i * 118
        out.append(text(sx, 238, str(value), size=26, fill=theme.text, weight=600))
        out.append(text(sx, 256, label, size=12, fill=theme.muted))
    out.append(f'<path d="M{x} 276H{WIDTH - PAD}" stroke="{theme.grid}"/>')
    out.append(text(x, 302, "LATEST MOVES", size=11, fill=theme.muted, weight=600, spacing=2))
    history = game.get("history", [])[:4]
    if not history:
        out.append(text(x, 328, "No moves yet — be the first.", size=13, fill=theme.text))
    for i, move in enumerate(history):
        y = 328 + i * 24
        who = f"@{move['player']}"
        line = f"{who} → {move['col']}" + (f"  ·  engine → {move['ai']}" if move.get("ai") else "")
        out.append(text(x, y, line[:52], size=13, fill=theme.text))
    if game["players"]:
        top = sorted(game["players"].items(), key=lambda kv: -kv[1])[:3]
        leaders = "Top players: " + ", ".join(f"@{name} ({n})" for name, n in top)
        out.append(text(x, HEIGHT - 26, leaders[:62], size=11.5, fill=theme.muted))

    summary = f"Connect Four, game {game['game_no']}: {title.lower()}. Visitors {stats['human']}, engine {stats['ai']}."
    return document(WIDTH, HEIGHT, "".join(out), title=summary, fonts=ctx.fonts, weights=(400, 600))


def render_button(ctx: Context, theme: Theme, column: int) -> str:
    w, h = 64, 40
    body = (f'<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="10" fill="{theme.surface}" '
            f'stroke="{theme.accent}"/>'
            f'<path d="M20 15v10m-4.5-4.5L20 25l4.5-4.5" fill="none" stroke="{theme.accent}" stroke-width="1.8" '
            f'stroke-linecap="round" stroke-linejoin="round"/>'
            + text(38, 25.5, str(column), size=15, fill=theme.text, weight=600, anchor="middle"))
    return document(w, h, body, title=f"Drop a disc in column {column}", fonts=ctx.fonts, weights=(600,))


def render(ctx: Context) -> None:
    if not ctx.config.game_enabled:
        return
    game = get_game(ctx.state)
    for theme in ctx.themes:
        ctx.write(f"game-{theme.name}.svg", render_board(ctx, theme, game))
        for column in range(1, c4.COLS + 1):
            ctx.write(f"game-col-{column}-{theme.name}.svg", render_button(ctx, theme, column))

