# SPDX-License-Identifier: MIT
# Copyright (c) 2026 John Luke NIKABOU (LucNIK)

"""Loads profile.toml and fills in sensible defaults."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class FocusItem:
    title: str
    lines: list[str]
    icon: str


@dataclass
class Config:
    user: str
    name: str
    website: str = ""
    copyright: str = ""
    font: str = "IBM Plex Sans"
    timezone: str = "UTC"
    light_accent: str | None = None
    dark_accent: str | None = None
    hero_lines: list[str] = field(default_factory=list)
    headings: list[str] = field(default_factory=list)
    focus: list[FocusItem] = field(default_factory=list)
    ticker_assets: list[dict] = field(default_factory=list)
    ticker_currency: str = "usd"
    ticker_gas: bool = True
    weekly_enabled: bool = True
    weekly_model: str = "openai/gpt-4.1-mini"
    weekly_exclude_repos: list[str] = field(default_factory=list)
    activity_enabled: bool = True
    activity_repos: int = 3
    activity_events: int = 5
    activity_posts: int = 3
    activity_rss: str = ""
    activity_exclude: list[str] = field(default_factory=list)


def load(path: str | Path) -> Config:
    raw = tomllib.loads(Path(path).read_text(encoding="utf-8"))
    profile = raw.get("profile", {})
    theme = raw.get("theme", {})
    hero = raw.get("hero", {})
    ticker = raw.get("ticker", {})
    weekly = raw.get("weekly", {})
    activity = raw.get("activity", {})
    if "user" not in profile:
        raise ValueError("profile.user is required in the config file")
    return Config(
        user=profile["user"],
        name=profile.get("name", profile["user"]),
        website=profile.get("website", ""),
        copyright=profile.get("copyright", ""),
        timezone=profile.get("timezone", "UTC"),
        font=theme.get("font", "IBM Plex Sans"),
        light_accent=theme.get("light_accent"),
        dark_accent=theme.get("dark_accent"),
        hero_lines=hero.get("lines") or [profile.get("name", profile["user"])],
        headings=raw.get("headings", {}).get("titles", []),
        focus=[FocusItem(i["title"], i.get("lines", []), i.get("icon", "spark"))
               for i in raw.get("focus", {}).get("items", [])],
        ticker_assets=ticker.get("assets", [
            {"id": "bitcoin", "symbol": "BTC", "name": "Bitcoin"},
            {"id": "ethereum", "symbol": "ETH", "name": "Ethereum"},
        ]),
        ticker_currency=ticker.get("currency", "usd"),
        ticker_gas=ticker.get("gas", True),
        weekly_enabled=weekly.get("enabled", True),
        weekly_model=weekly.get("model", "openai/gpt-4.1-mini"),
        weekly_exclude_repos=weekly.get("exclude_repos", []),
        activity_enabled=activity.get("enabled", True),
        activity_repos=activity.get("repos", 3),
        activity_events=activity.get("events", 5),
        activity_posts=activity.get("posts", 3),
        activity_rss=activity.get("rss", ""),
        activity_exclude=activity.get("exclude_repos", []),
    )
