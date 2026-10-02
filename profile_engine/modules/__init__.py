# SPDX-License-Identifier: MIT
# Copyright (c) 2026 John Luke NIKABOU (LucNIK)

"""Renderable modules. Each exposes `render(ctx)` and writes `<name>-light.svg` / `<name>-dark.svg`."""

from . import activity, badges, focus, headings, hero, ticker, weekly

REGISTRY = {
    "hero": hero.render,
    "headings": headings.render,
    "focus": focus.render,
    "badges": badges.render,
    "activity": activity.render,
    "ticker": ticker.render,
    "weekly": weekly.render,
}
