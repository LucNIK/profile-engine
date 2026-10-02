# SPDX-License-Identifier: MIT
# Copyright (c) 2026 John Luke NIKABOU (LucNIK)

"""Shared runtime context handed to every module."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from .config import Config
from .fonts import FontKit
from .theme import Theme, themes

STATE_FILE = "engine-state.json"


@dataclass
class Context:
    config: Config
    out_dir: Path
    fonts: FontKit
    light: Theme
    dark: Theme
    now: datetime
    offline: bool = False
    token: str = ""
    state: dict = field(default_factory=dict)

    @property
    def themes(self) -> tuple[Theme, Theme]:
        return self.light, self.dark

    def save_state(self) -> None:
        (self.out_dir / STATE_FILE).write_text(json.dumps(self.state, indent=2, sort_keys=True))

    def write(self, name: str, svg: str) -> None:
        notice = self.config.copyright.replace("--", "–").strip()
        if notice:  # an XML comment before the root element: invisible, but travels with the file
            svg = f"<!-- {notice} -->\n{svg}"
        (self.out_dir / name).write_text(svg, encoding="utf-8")


def build(config: Config, out_dir: Path, *, offline: bool = False, now: datetime | None = None) -> Context:
    out_dir.mkdir(parents=True, exist_ok=True)
    state_path = out_dir / STATE_FILE
    state = json.loads(state_path.read_text()) if state_path.exists() else {}
    light, dark = themes(config.light_accent, config.dark_accent)
    tz = ZoneInfo(config.timezone)
    return Context(
        config=config,
        out_dir=out_dir,
        fonts=FontKit(config.font, out_dir / "fonts", offline=offline),
        light=light,
        dark=dark,
        now=(now or datetime.now(tz)).astimezone(tz),
        offline=offline,
        token=os.environ.get("GITHUB_TOKEN", ""),
        state=state,
    )
