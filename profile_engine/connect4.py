# SPDX-License-Identifier: MIT
# Copyright (c) 2026 John Luke NIKABOU (LucNIK)

"""Connect Four rules and the engine's opponent: minimax with alpha-beta pruning.

The board is a list of 7 columns, each a list of discs from bottom to top:
1 = visitors (humans), 2 = the engine (AI).
"""

from __future__ import annotations

import re

ROWS, COLS = 6, 7
HUMAN, AI = 1, 2
MOVE_PATTERN = re.compile(r"^\s*connect4\s*\|\s*drop\s*\|\s*([1-7])\s*$", re.IGNORECASE)
CENTER_FIRST = (3, 2, 4, 1, 5, 0, 6)


def parse_move(title: str) -> int | None:
    """Column index (0-6) from an issue title like 'connect4|drop|4', or None if invalid."""
    match = MOVE_PATTERN.match(title or "")
    return int(match.group(1)) - 1 if match else None


def empty_board() -> list[list[int]]:
    return [[] for _ in range(COLS)]


def legal_moves(board: list[list[int]]) -> list[int]:
    return [c for c in CENTER_FIRST if len(board[c]) < ROWS]


def drop(board: list[list[int]], col: int, player: int) -> list[list[int]]:
    if not 0 <= col < COLS or len(board[col]) >= ROWS:
        raise ValueError(f"column {col + 1} is full")
    new = [column[:] for column in board]
    new[col].append(player)
    return new


def cell(board: list[list[int]], col: int, row: int) -> int:
    column = board[col]
    return column[row] if row < len(column) else 0


def winning_line(board: list[list[int]]) -> list[tuple[int, int]] | None:
    """The four (col, row) cells of a winning line, if any."""
    for col in range(COLS):
        for row in range(len(board[col])):
            player = board[col][row]
            for dc, dr in ((1, 0), (0, 1), (1, 1), (1, -1)):
                line = [(col + i * dc, row + i * dr) for i in range(4)]
                if all(0 <= c < COLS and 0 <= r < ROWS and cell(board, c, r) == player for c, r in line):
                    return line
    return None


def winner(board: list[list[int]]) -> int:
    line = winning_line(board)
    return cell(board, *line[0]) if line else 0


def is_full(board: list[list[int]]) -> bool:
    return all(len(column) == ROWS for column in board)


# ------------------------------------------------------------------ AI

def _score_window(window: list[int], player: int) -> int:
    other = HUMAN if player == AI else AI
    mine, theirs, empty = window.count(player), window.count(other), window.count(0)
    if mine == 4:
        return 1000
    if mine == 3 and empty == 1:
        return 6
    if mine == 2 and empty == 2:
        return 2
    if theirs == 3 and empty == 1:
        return -8
    return 0


def evaluate(board: list[list[int]], player: int = AI) -> int:
    score = 3 * sum(1 for row in range(ROWS) if cell(board, 3, row) == player)
    for col in range(COLS):
        for row in range(ROWS):
            for dc, dr in ((1, 0), (0, 1), (1, 1), (1, -1)):
                end_c, end_r = col + 3 * dc, row + 3 * dr
                if 0 <= end_c < COLS and 0 <= end_r < ROWS:
                    window = [cell(board, col + i * dc, row + i * dr) for i in range(4)]
                    score += _score_window(window, player)
    return score


def _minimax(board, depth, alpha, beta, maximizing) -> tuple[int, int | None]:
    won = winner(board)
    if won == AI:
        return 100_000 + depth, None   # prefer faster wins
    if won == HUMAN:
        return -100_000 - depth, None  # prefer slower losses
    moves = legal_moves(board)
    if not moves:
        return 0, None
    if depth == 0:
        return evaluate(board), None
    best_move = moves[0]
    if maximizing:
        value = -10**9
        for col in moves:
            score, _ = _minimax(drop(board, col, AI), depth - 1, alpha, beta, False)
            if score > value:
                value, best_move = score, col
            alpha = max(alpha, value)
            if alpha >= beta:
                break
    else:
        value = 10**9
        for col in moves:
            score, _ = _minimax(drop(board, col, HUMAN), depth - 1, alpha, beta, True)
            if score < value:
                value, best_move = score, col
            beta = min(beta, value)
            if alpha >= beta:
                break
    return value, best_move


def best_move(board: list[list[int]], depth: int = 6) -> int:
    """The engine's reply. Depth 6 looks three full turns ahead — strong but beatable."""
    _, move = _minimax(board, depth, -10**9, 10**9, True)
    if move is None:
        raise ValueError("no legal move")
    return move
