# SPDX-License-Identifier: MIT
# Copyright (c) 2026 John Luke NIKABOU (LucNIK)

"""Section headings: numbered, letter-spaced, with accent rules — `01 ── ABOUT ──`."""

from __future__ import annotations

import re

from ..context import Context
from ..svg import document, text, text_width
from ..theme import Theme

WIDTH, HEIGHT = 840, 44
SIZE, SPACING = 15, 6


def slug(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")


def render_theme(ctx: Context, theme: Theme, index: int, title: str) -> str:
    label = title.upper()
    number = f"{index:02d}"
    cy = HEIGHT / 2
    num_w = text_width(number, 12, 600, 2)
    label_w = text_width(label, SIZE, 600, SPACING)
    gap, rule = 14, 56
    total = num_w + gap + label_w
    x = WIDTH / 2 - total / 2
    body = [
        text(x, cy + 4.5, number, size=12, fill=theme.muted, weight=600, spacing=2, mono=True),
        text(x + num_w + gap, cy + 5.5, label, size=SIZE, fill=theme.accent, weight=600, spacing=SPACING),
        f'<path d="M{x - gap - rule:.1f} {cy}h{rule}" stroke="{theme.accent}" stroke-width="1.2" opacity=".55"/>',
        f'<path d="M{x + total + gap - SPACING:.1f} {cy}h{rule}" stroke="{theme.accent}" '
        f'stroke-width="1.2" opacity=".55"/>',
        f'<rect x="{x - gap - rule - 6:.1f}" y="{cy - 2}" width="4" height="4" transform="rotate(45 '
        f'{x - gap - rule - 4:.1f} {cy})" fill="{theme.accent}"/>',
        f'<rect x="{x + total + gap - SPACING + rule + 2:.1f}" y="{cy - 2}" width="4" height="4" '
        f'transform="rotate(45 {x + total + gap - SPACING + rule + 4:.1f} {cy})" fill="{theme.accent}"/>',
    ]
    return document(WIDTH, HEIGHT, "".join(body), title=title, fonts=ctx.fonts, weights=(600,))


def render(ctx: Context) -> None:
    for i, title in enumerate(ctx.config.headings, start=1):
        for theme in ctx.themes:
            ctx.write(f"heading-{slug(title)}-{theme.name}.svg", render_theme(ctx, theme, i, title))
