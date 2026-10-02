"""Focus areas as a row of icon cards."""

from __future__ import annotations

from ..context import Context
from ..icons import icon
from ..svg import card, document, text
from ..theme import Theme

WIDTH = 840
CARD_H, GAP = 150, 14


def render_theme(ctx: Context, theme: Theme) -> str:
    items = ctx.config.focus
    n = max(len(items), 1)
    card_w = (WIDTH - 2 - GAP * (n - 1)) / n
    body = []
    for i, item in enumerate(items):
        x = 1 + i * (card_w + GAP)
        cx = x + card_w / 2
        body.append(card(x, 1, card_w, CARD_H - 2, theme))
        body.append(f'<path d="M{x + 22:.1f} 1.5h{card_w - 44:.1f}" stroke="{theme.accent}" stroke-width="2" '
                    f'stroke-linecap="round"/>')
        body.append(icon(item.icon, cx - 16, 22, 32, theme.accent, stroke=1.7))
        body.append(text(cx, 82, item.title, size=16, fill=theme.text, weight=600, anchor="middle"))
        for j, line in enumerate(item.lines[:2]):
            body.append(text(cx, 106 + j * 18, line, size=12.5, fill=theme.muted, anchor="middle"))
    title = "Focus: " + ", ".join(item.title for item in items)
    return document(WIDTH, CARD_H, "".join(body), title=title, fonts=ctx.fonts, weights=(400, 600))


def render(ctx: Context) -> None:
    if not ctx.config.focus:
        return
    for theme in ctx.themes:
        ctx.write(f"focus-{theme.name}.svg", render_theme(ctx, theme))
