# SPDX-License-Identifier: MIT
# Copyright (c) 2026 John Luke NIKABOU (LucNIK)

"""SVG building blocks shared by every module."""

from __future__ import annotations

from xml.sax.saxutils import escape as _escape

from .fonts import FontKit
from .theme import Theme

FONT_STACK = "'IBM Plex Sans', 'Segoe UI', 'Helvetica Neue', Arial, sans-serif"
MONO_STACK = "'IBM Plex Mono', 'SFMono-Regular', Consolas, monospace"


def esc(text: object) -> str:
    return _escape(str(text), {'"': "&quot;"})


def document(width: int, height: int, body: str, *, title: str, fonts: FontKit,
             weights: tuple[int, ...] = (400, 600), extra_css: str = "") -> str:
    """Wrap a body in a standalone, accessible SVG document with embedded fonts."""
    css = fonts.css(weights) + extra_css
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-label="{esc(title)}">'
        f"<title>{esc(title)}</title>"
        f"<style>svg{{font-family:{FONT_STACK}}}{css}</style>"
        f"{body}</svg>\n"
    )


def card(x: float, y: float, w: float, h: float, theme: Theme, r: float = 12) -> str:
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" '
            f'fill="{theme.surface}" stroke="{theme.border}" stroke-width="1"/>')


def text(x: float, y: float, value: str, *, size: float, fill: str, weight: int = 400,
         anchor: str = "start", spacing: float = 0, mono: bool = False, extra: str = "") -> str:
    family = f' font-family="{MONO_STACK}"' if mono else ""
    ls = f' letter-spacing="{spacing}"' if spacing else ""
    return (f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" fill="{fill}" '
            f'text-anchor="{anchor}"{ls}{family}{extra}>{esc(value)}</text>')


def text_width(value: str, size: float, weight: int = 400, spacing: float = 0) -> float:
    """Approximate rendered width for IBM Plex Sans (good enough for layout and clipping)."""
    narrow = set("iljtfr.,:;'!|I ")
    wide = set("MWmw@%")
    units = 0.0
    for ch in value:
        if ch in narrow:
            units += 0.32
        elif ch in wide:
            units += 0.86
        elif ch.isupper() or ch.isdigit():
            units += 0.64
        else:
            units += 0.54
    bold = 1.04 if weight >= 600 else 1.0
    return units * size * bold + spacing * max(len(value) - 1, 0)


def wrap(value: str, size: float, max_width: float) -> list[str]:
    """Greedy word wrap using the width estimate above."""
    lines: list[str] = []
    current = ""
    for word in value.split():
        candidate = f"{current} {word}".strip()
        if text_width(candidate, size) <= max_width * 0.97 or not current:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def sparkline(points: list[float], x: float, y: float, w: float, h: float, *, stroke: str,
              fill_id: str) -> str:
    """Smooth-ish polyline with a soft gradient area underneath."""
    if len(points) < 2:
        return ""
    lo, hi = min(points), max(points)
    span = (hi - lo) or 1.0
    step = w / (len(points) - 1)
    coords = [(x + i * step, y + h - (p - lo) / span * h) for i, p in enumerate(points)]
    line = " ".join(f"{px:.1f},{py:.1f}" for px, py in coords)
    area = f"{x:.1f},{y + h:.1f} {line} {x + w:.1f},{y + h:.1f}"
    return (
        f'<defs><linearGradient id="{fill_id}" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="{stroke}" stop-opacity="0.28"/>'
        f'<stop offset="1" stop-color="{stroke}" stop-opacity="0"/></linearGradient></defs>'
        f'<polygon points="{area}" fill="url(#{fill_id})"/>'
        f'<polyline points="{line}" fill="none" stroke="{stroke}" stroke-width="1.8" '
        f'stroke-linejoin="round" stroke-linecap="round"/>'
    )
