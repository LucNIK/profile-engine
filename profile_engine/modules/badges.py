# SPDX-License-Identifier: MIT
# Copyright (c) 2026 John Luke NIKABOU (LucNIK)

"""Link badges (website, followers) drawn in the profile's own style."""

from __future__ import annotations

from ..context import Context
from ..github import GitHub
from ..icons import icon
from ..svg import document, text, text_width
from ..theme import Theme

HEIGHT = 36


def badge(ctx: Context, theme: Theme, glyph: str, label: str, value: str | None) -> str:
    label_w = text_width(label, 12, 600, 1.6)
    pill_w = max(text_width(value, 12, 600) + 22, 30) if value else 0
    text_x = 16 + 18 + 9
    width = text_x + label_w + (10 + pill_w + 5 if value else 18)
    body = [
        f'<rect x=".5" y=".5" width="{width - 1:.1f}" height="{HEIGHT - 1}" rx="{(HEIGHT - 1) / 2}" '
        f'fill="{theme.surface}" stroke="{theme.accent}" stroke-width="1"/>',
        icon(glyph, 16, (HEIGHT - 18) / 2, 18, theme.accent, stroke=1.7),
        text(text_x, HEIGHT / 2 + 4.3, label, size=12, fill=theme.text, weight=600, spacing=1.6),
    ]
    if value:
        px = width - 5 - pill_w
        body.append(f'<rect x="{px:.1f}" y="5" width="{pill_w:.1f}" height="{HEIGHT - 10}" '
                    f'rx="{(HEIGHT - 10) / 2}" fill="{theme.accent}"/>')
        body.append(text(px + pill_w / 2, HEIGHT / 2 + 4.3, value, size=12, fill=theme.surface, weight=600,
                         anchor="middle"))
    title = f"{label} {value}" if value else label
    return document(int(width + 0.99), HEIGHT, "".join(body), title=title, fonts=ctx.fonts, weights=(600,))


def render(ctx: Context) -> None:
    cfg = ctx.config
    followers = ctx.state.get("followers")
    if not ctx.offline:
        try:
            followers = GitHub(ctx.token).user(cfg.user)["followers"]
            ctx.state["followers"] = followers
        except Exception as exc:  # keep the last known value
            print(f"[badges] {exc}")
    for theme in ctx.themes:
        if cfg.website:
            host = cfg.website.split("//")[-1].strip("/").upper()
            ctx.write(f"badge-website-{theme.name}.svg", badge(ctx, theme, "globe", host, None))
        ctx.write(f"badge-followers-{theme.name}.svg",
                  badge(ctx, theme, "users", "FOLLOWERS", str(followers if followers is not None else "—")))
