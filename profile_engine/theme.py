# SPDX-License-Identifier: MIT
# Copyright (c) 2026 John Luke NIKABOU (LucNIK)

"""Design tokens. Every visual is rendered twice: once per theme."""

from __future__ import annotations

from dataclasses import dataclass, replace


@dataclass(frozen=True)
class Theme:
    name: str            # "light" | "dark"
    accent: str          # brand colour (gold by day, bordeaux by night)
    text: str            # primary text
    muted: str           # secondary text
    surface: str         # card background
    border: str          # card border
    grid: str            # hairlines, sparkline baseline
    up: str              # positive change
    down: str            # negative change


LIGHT = Theme(
    name="light",
    accent="#B7860B",
    text="#1F2328",
    muted="#59636E",
    surface="#FFFFFF",
    border="#D1D9E0",
    grid="#EAEEF2",
    up="#1A7F37",
    down="#CF222E",
)

DARK = Theme(
    name="dark",
    accent="#C1121F",
    text="#E6EDF3",
    muted="#8B949E",
    surface="#0D1117",
    border="#30363D",
    grid="#21262D",
    up="#3FB950",
    down="#F85149",
)


def themes(light_accent: str | None = None, dark_accent: str | None = None) -> tuple[Theme, Theme]:
    """Return (light, dark), optionally overriding the accent colours from config."""
    light = replace(LIGHT, accent=light_accent) if light_accent else LIGHT
    dark = replace(DARK, accent=dark_accent) if dark_accent else DARK
    return light, dark
