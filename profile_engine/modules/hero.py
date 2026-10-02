# SPDX-License-Identifier: MIT
# Copyright (c) 2026 John Luke NIKABOU (LucNIK)

"""Animated hero title: each line types itself out, holds, then erases — pure CSS, no JS.

Honours `prefers-reduced-motion` by showing the first line statically.
"""

from __future__ import annotations

from ..context import Context
from ..svg import document, esc, text_width
from ..theme import Theme

WIDTH, HEIGHT = 840, 76
SIZE, WEIGHT, SPACING = 30, 700, 3


def _pct(value: float, total: float) -> str:
    return f"{value / total * 100:.3f}%"


def render_theme(ctx: Context, theme: Theme) -> str:
    lines = [line.upper() for line in ctx.config.hero_lines]
    timings = []
    t = 0.0
    for line in lines:
        typing = min(max(0.065 * len(line), 0.8), 1.7)
        timings.append((t, typing, 1.8, 0.45))
        t += typing + 1.8 + 0.45 + 0.25
    total = t

    css = [
        ".g{opacity:0}",
        ".k{animation:blink 1s steps(1) infinite}",
        "@keyframes blink{50%{opacity:0}}",
    ]
    body = []
    cx, baseline = WIDTH / 2, HEIGHT / 2 + SIZE * 0.36
    for i, (line, (start, typing, hold, erase)) in enumerate(zip(lines, timings)):
        w = text_width(line, SIZE, WEIGHT, SPACING)
        x0 = cx - w / 2
        a, b = _pct(start, total), _pct(start + typing, total)
        c, d = _pct(start + typing + hold, total), _pct(start + typing + hold + erase, total)
        d2 = _pct(min(start + typing + hold + erase + 0.01, total), total)
        steps = max(len(line), 1)
        css.append(
            f"@keyframes s{i}{{0%,{a}{{transform:scaleX(0);animation-timing-function:steps({steps},end)}}"
            f"{b},{c}{{transform:scaleX(1);animation-timing-function:ease-in}}{d},100%{{transform:scaleX(0)}}}}"
            f"@keyframes m{i}{{0%,{a}{{transform:translateX(0);animation-timing-function:steps({steps},end)}}"
            f"{b},{c}{{transform:translateX({w:.1f}px);animation-timing-function:ease-in}}"
            f"{d},100%{{transform:translateX(0)}}}}"
            f"@keyframes o{i}{{0%{{opacity:0}}{a},{d}{{opacity:1}}{d2},100%{{opacity:0}}}}"
            f".r{i}{{transform-box:fill-box;transform-origin:left center;"
            f"animation:s{i} {total:.2f}s infinite both}}"
            f".c{i}{{animation:m{i} {total:.2f}s infinite both}}"
            f".g{i}{{animation:o{i} {total:.2f}s infinite both}}"
        )
        body.append(
            f'<clipPath id="clip{i}"><rect class="r{i}" x="{x0 - 2:.1f}" y="0" '
            f'width="{w + 4:.1f}" height="{HEIGHT}"/></clipPath>'
            f'<g class="g g{i}">'
            f'<text x="{cx}" y="{baseline:.1f}" text-anchor="middle" font-size="{SIZE}" '
            f'font-weight="{WEIGHT}" letter-spacing="{SPACING}" fill="{theme.accent}" '
            f'clip-path="url(#clip{i})">{esc(line)}</text>'
            f'<g class="c{i}"><rect class="k" x="{x0 + 4:.1f}" y="{baseline - SIZE * 0.78:.1f}" '
            f'width="3" height="{SIZE * 0.95:.1f}" rx="1" fill="{theme.accent}"/></g></g>'
        )
    css.append(
        "@media (prefers-reduced-motion:reduce){.g,.g0,[class^=r],[class^=c],.k{animation:none!important}"
        ".g0{opacity:1}.r0{transform:none}}"
    )
    return document(WIDTH, HEIGHT, "".join(body), title=" · ".join(ctx.config.hero_lines),
                    fonts=ctx.fonts, weights=(WEIGHT,), extra_css="".join(css))


def render(ctx: Context) -> None:
    for theme in ctx.themes:
        ctx.write(f"hero-{theme.name}.svg", render_theme(ctx, theme))
