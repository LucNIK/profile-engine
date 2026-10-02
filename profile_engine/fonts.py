# SPDX-License-Identifier: MIT
# Copyright (c) 2026 John Luke NIKABOU (LucNIK)

"""Embeds IBM Plex Sans into every SVG.

GitHub serves README images through a proxy that forbids external requests from inside an SVG,
so the font must travel *inside* the file as base64. Fonts are downloaded once from Google Fonts
and cached in the output directory; if the download fails we fall back to the system stack.
"""

from __future__ import annotations

import base64
import re
from pathlib import Path

from .net import FetchError, fetch

GOOGLE_CSS = "https://fonts.googleapis.com/css2?family={family}:wght@{weights}&display=swap"
# A modern browser UA makes Google Fonts answer with woff2 sources.
BROWSER_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")


class FontKit:
    def __init__(self, family: str, cache_dir: Path, *, offline: bool = False,
                 weights: tuple[int, ...] = (400, 600, 700)) -> None:
        self.family = family
        self.cache_dir = cache_dir
        self.files: dict[int, bytes] = {}
        self._load(weights, offline)

    def _cache_path(self, weight: int) -> Path:
        slug = re.sub(r"[^a-z0-9]+", "-", self.family.lower()).strip("-")
        return self.cache_dir / f"{slug}-{weight}.woff2"

    def _load(self, weights: tuple[int, ...], offline: bool) -> None:
        missing = []
        for w in weights:
            path = self._cache_path(w)
            if path.exists():
                self.files[w] = path.read_bytes()
            else:
                missing.append(w)
        if not missing or offline:
            return
        try:
            css = fetch(
                GOOGLE_CSS.format(family=self.family.replace(" ", "+"),
                                  weights=";".join(map(str, missing))),
                headers={"User-Agent": BROWSER_UA},
            ).decode()
        except FetchError as exc:
            print(f"[fonts] {exc} — falling back to system fonts")
            return
        downloaded: dict[str, bytes] = {}
        for w, url in _latin_sources(css).items():
            # Variable fonts are served as one file for every weight: download it once.
            if url not in downloaded:
                try:
                    downloaded[url] = fetch(url, headers={"User-Agent": BROWSER_UA})
                except FetchError as exc:
                    print(f"[fonts] {exc}")
                    continue
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            self._cache_path(w).write_bytes(downloaded[url])
            self.files[w] = downloaded[url]

    def css(self, weights: tuple[int, ...]) -> str:
        """@font-face rules for the requested weights, embedding each distinct file only once.

        When several weights share the same bytes it is a variable font, declared with a weight range.
        """
        groups: dict[bytes, list[int]] = {}
        for w in weights:
            data = self.files.get(w)
            if data:
                groups.setdefault(data, []).append(w)
        rules = []
        for data, ws in groups.items():
            weight = str(ws[0]) if len(ws) == 1 and self._is_static(data) else "100 900"
            b64 = base64.b64encode(data).decode()
            rules.append(
                f"@font-face{{font-family:'{self.family}';font-weight:{weight};"
                f"src:url(data:font/woff2;base64,{b64}) format('woff2')}}"
            )
        return "".join(rules)

    def _is_static(self, data: bytes) -> bool:
        """A file shared by several cached weights is a variable font."""
        return sum(1 for d in self.files.values() if d == data) == 1


def _latin_sources(css: str) -> dict[int, str]:
    """Pick the basic-latin woff2 URL for each weight from a Google Fonts stylesheet."""
    found: dict[int, str] = {}
    for comment, block in re.findall(r"/\*\s*([\w-]+)\s*\*/\s*@font-face\s*{([^}]*)}", css):
        if comment != "latin":
            continue
        weight = re.search(r"font-weight:\s*(\d+)", block)
        url = re.search(r"url\((https://[^)]+\.woff2)\)", block)
        if weight and url:
            found[int(weight.group(1))] = url.group(1)
    return found
