# SPDX-License-Identifier: MIT
# Copyright (c) 2026 John Luke NIKABOU (LucNIK)

"""Hand-drawn 24×24 line icons — no icon font, no CDN, nothing that can break."""

from __future__ import annotations

ICONS: dict[str, str] = {
    # neural network: input, hidden and output nodes
    "network": (
        '<path d="M6.5 7l4 4.2M6.5 17l4-4.2M13.5 11.2l4-4.2M13.5 12.8l4 4.2M7 6h10M7 18h10"/>'
        '<circle cx="5" cy="6" r="2"/><circle cx="5" cy="18" r="2"/><circle cx="12" cy="12" r="2"/>'
        '<circle cx="19" cy="6" r="2"/><circle cx="19" cy="18" r="2"/>'
    ),
    # two trading candles
    "candles": (
        '<path d="M8 3v4M8 15v6M16 5v4M16 15v4"/>'
        '<rect x="6" y="7" width="4" height="8" rx="1"/><rect x="14" y="9" width="4" height="6" rx="1"/>'
    ),
    # ethereum diamond
    "ethereum": '<path d="M12 2.5l6.5 9.8L12 16l-6.5-3.7z"/><path d="M5.5 14.2L12 21.5l6.5-7.3L12 18z"/>',
    "cloud": '<path d="M7 18.5h10a4.25 4.25 0 0 0 .6-8.46A6 6 0 0 0 6.1 9.4 4.6 4.6 0 0 0 7 18.5z"/>',
    "gas": (
        '<rect x="4" y="4" width="9" height="16" rx="1.5"/><path d="M4 10h9"/>'
        '<path d="M13 8h1.5a2 2 0 0 1 2 2v5.5a1.5 1.5 0 0 0 3 0V8.5L17 6"/>'
    ),
    "spark": (
        '<path d="M11 3l1.9 5.6L18.5 10.5l-5.6 1.9L11 18l-1.9-5.6L3.5 10.5l5.6-1.9z"/>'
        '<path d="M18.5 15.5l.8 2.2 2.2.8-2.2.8-.8 2.2-.8-2.2-2.2-.8 2.2-.8z"/>'
    ),
    "globe": '<circle cx="12" cy="12" r="9"/><ellipse cx="12" cy="12" rx="4" ry="9"/><path d="M3 12h18"/>',
    "users": (
        '<circle cx="9" cy="8" r="3.5"/><path d="M2.5 20a6.5 6.5 0 0 1 13 0"/>'
        '<circle cx="17" cy="9" r="2.5"/><path d="M16.5 14.6A5 5 0 0 1 21.5 20"/>'
    ),
    "arrow": '<path d="M7 17L17 7M9 7h8v8"/>',
    "coin": '<circle cx="12" cy="12" r="9"/><path d="M9.5 8h4a2 2 0 0 1 0 4h-4zM9.5 12h4.5a2 2 0 0 1 0 4H9.5zM9.5 8v8M11 6.5V8M11 16v1.5"/>',
}


def icon(name: str, x: float, y: float, size: float, color: str, stroke: float = 1.6) -> str:
    """Place a named icon at (x, y) scaled to `size` pixels."""
    body = ICONS[name]
    scale = size / 24
    return (
        f'<g transform="translate({x} {y}) scale({scale:.4f})" fill="none" stroke="{color}" '
        f'stroke-width="{stroke / scale:.2f}" stroke-linecap="round" stroke-linejoin="round">'
        f"{body}</g>"
    )
