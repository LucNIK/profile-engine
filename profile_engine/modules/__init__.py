"""Renderable modules. Each exposes `render(ctx)` and writes `<name>-light.svg` / `<name>-dark.svg`."""

from . import badges, focus, headings, hero, ticker, weekly

REGISTRY = {
    "hero": hero.render,
    "headings": headings.render,
    "focus": focus.render,
    "badges": badges.render,
    "ticker": ticker.render,
    "weekly": weekly.render,
}
