"""Offline test suite — runs with the standard library only: `python -m unittest`."""

from __future__ import annotations

import json
import tempfile
import unittest
import xml.dom.minidom
from datetime import datetime
from pathlib import Path
from unittest import mock
from zoneinfo import ZoneInfo

from profile_engine import __main__ as cli
from profile_engine.config import load
from profile_engine.fonts import _latin_sources
from profile_engine.modules import ticker, weekly
from profile_engine.svg import text_width, wrap

ROOT = Path(__file__).resolve().parent.parent
EXAMPLE = ROOT / "examples" / "profile.toml"


class EngineRunTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.out = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_offline_run_writes_valid_light_and_dark_svgs(self) -> None:
        self.assertEqual(cli.main(["--config", str(EXAMPLE), "--out", str(self.out), "--offline"]), 0)
        svgs = sorted(self.out.glob("*.svg"))
        names = {p.name for p in svgs}
        for base in ["hero", "focus", "ticker", "weekly", "badge-website", "badge-followers",
                     "heading-about", "heading-this-week"]:
            self.assertIn(f"{base}-light.svg", names)
            self.assertIn(f"{base}-dark.svg", names)
        for path in svgs:
            doc = xml.dom.minidom.parse(str(path))  # raises on malformed XML
            root = doc.documentElement
            self.assertEqual(root.tagName, "svg")
            self.assertEqual(root.getAttribute("role"), "img")
            self.assertTrue(root.getElementsByTagName("title"), f"{path.name} lacks an accessible title")
            self.assertNotIn("http://", path.read_text().replace("http://www.w3.org/2000/svg", ""),
                             f"{path.name} must not load external resources")

    def test_themes_use_their_own_accent(self) -> None:
        cli.main(["--config", str(EXAMPLE), "--out", str(self.out), "--offline", "--modules", "focus"])
        self.assertIn("#B7860B", (self.out / "focus-light.svg").read_text())
        self.assertIn("#C1121F", (self.out / "focus-dark.svg").read_text())
        self.assertNotIn("#C1121F", (self.out / "focus-light.svg").read_text())

    def test_state_is_persisted(self) -> None:
        cli.main(["--config", str(EXAMPLE), "--out", str(self.out), "--offline"])
        state = json.loads((self.out / "engine-state.json").read_text())
        self.assertIn("ticker", state)
        self.assertIn("weekly", state)

    def test_unknown_module_is_rejected(self) -> None:
        with self.assertRaises(SystemExit):
            cli.main(["--config", str(EXAMPLE), "--out", str(self.out), "--modules", "nope"])


class WeeklyTest(unittest.TestCase):
    def test_fallback_summary_counts(self) -> None:
        stats = weekly.stats_for([
            {"repo": "a/x", "message": "m"}, {"repo": "a/x", "message": "m"}, {"repo": "a/y", "message": "m"},
        ])
        self.assertEqual(stats, {"commits": 3, "repos": 2, "top": ["x", "y"]})
        self.assertIn("3 commits across 2 repositories", weekly.fallback_summary(stats))
        self.assertIn("1 commit across 1 repository",
                      weekly.fallback_summary({"commits": 1, "repos": 1, "top": ["x"]}))

    def test_summary_is_cached_per_iso_week(self) -> None:
        cfg = load(EXAMPLE)
        ctx = mock.Mock(config=cfg, offline=True, token="", now=datetime(2026, 10, 2, tzinfo=ZoneInfo("UTC")))
        ctx.state = {"weekly": {"week": "2026-W40", "summary": "cached", "source": "auto",
                                "range": ["2026-09-25", "2026-10-02"], "commits": 0, "repos": 0, "top": []}}
        self.assertEqual(weekly.collect(ctx)["summary"], "cached")
        ctx.now = datetime(2026, 10, 6, tzinfo=ZoneInfo("UTC"))  # next ISO week
        self.assertNotEqual(weekly.collect(ctx)["summary"], "cached")


class TickerTest(unittest.TestCase):
    def test_price_and_change_formatting(self) -> None:
        self.assertEqual(ticker.format_price(64250.4, "usd"), "$64,250")
        self.assertEqual(ticker.format_price(3.14159, "eur"), "€3.14")
        self.assertEqual(ticker.format_price(None, "usd"), "—")
        self.assertEqual(ticker.format_change(-1.234), "▼ 1.23%")
        self.assertEqual(ticker.format_change(0.5), "▲ 0.50%")

    def test_timestamp_uses_explicit_offset(self) -> None:
        moment = datetime(2026, 10, 2, 9, 5, tzinfo=ZoneInfo("Asia/Shanghai"))
        self.assertEqual(ticker.stamp(moment), "Oct 2, 09:05 UTC+8")

    def test_downsample_keeps_last_point(self) -> None:
        points = list(range(300))
        sampled = ticker._downsample(points, 48)
        self.assertEqual(sampled[-1], 299)
        self.assertLessEqual(len(sampled), 49)


class LayoutTest(unittest.TestCase):
    def test_wrap_respects_width(self) -> None:
        sentence = "word " * 80
        for line in wrap(sentence, 15, 400):
            self.assertLessEqual(text_width(line, 15), 400)

    def test_google_fonts_latin_block_is_selected(self) -> None:
        css = """
        /* cyrillic */ @font-face { font-weight: 400; src: url(https://x/cyr.woff2) format('woff2'); }
        /* latin */ @font-face { font-weight: 400; src: url(https://x/lat400.woff2) format('woff2'); }
        /* latin */ @font-face { font-weight: 700; src: url(https://x/lat700.woff2) format('woff2'); }
        """
        self.assertEqual(_latin_sources(css), {400: "https://x/lat400.woff2", 700: "https://x/lat700.woff2"})


if __name__ == "__main__":
    unittest.main()
