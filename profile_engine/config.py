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


def load(path: str | Path) -> Config:
    raw = tomllib.loads(Path(path).read_text(encoding="utf-8"))
    profile = raw.get("profile", {})
    theme = raw.get("theme", {})
    hero = raw.get("hero", {})
    ticker = raw.get("ticker", {})
    weekly = raw.get("weekly", {})
    if "user" not in profile:
        raise ValueError("profile.user is required in the config file")
    return Config(
        user=profile["user"],
        name=profile.get("name", profile["user"]),
        website=profile.get("website", ""),
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
    )
