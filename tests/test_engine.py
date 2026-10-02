# SPDX-License-Identifier: MIT
# Copyright (c) 2026 John Luke NIKABOU (LucNIK)

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
from profile_engine import connect4 as c4
from profile_engine.modules import activity, game, ticker, weekly
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
        for base in ["hero", "focus", "ticker", "weekly", "activity", "game", "game-col-1", "game-col-7", "badge-website", "badge-followers",
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

    def test_copyright_notice_travels_with_every_svg(self) -> None:
        cli.main(["--config", str(EXAMPLE), "--out", str(self.out), "--offline"])
        for path in self.out.glob("*.svg"):
            self.assertTrue(path.read_text().startswith("<!-- © 2026 John Luke NIKABOU"), path.name)

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


class ActivityTest(unittest.TestCase):
    def test_events_are_described_and_pushes_merged(self) -> None:
        events = [
            {"type": "PushEvent", "repo": {"name": "LucNIK/engine"}, "payload": {"size": 2}, "created_at": "t1"},
            {"type": "PushEvent", "repo": {"name": "LucNIK/engine"}, "payload": {"size": 3}, "created_at": "t2"},
            {"type": "WatchEvent", "repo": {"name": "other/lib"}, "payload": {}, "created_at": "t3"},
            {"type": "GollumEvent", "repo": {"name": "LucNIK/wiki"}, "payload": {}, "created_at": "t4"},
            {"type": "PullRequestEvent", "repo": {"name": "LucNIK/app"},
             "payload": {"action": "closed", "pull_request": {"number": 7, "merged": True}}, "created_at": "t5"},
        ]
        rows = activity.summarize_events(events, "LucNIK", 10)
        self.assertEqual([r["text"] for r in rows],
                         ["Pushed 5 commits to engine", "Starred other/lib", "Merged PR #7 in app"])

    def test_repos_skip_forks_archived_and_profile_repo(self) -> None:
        repos = [
            {"name": "LucNIK", "fork": False}, {"name": "fork", "fork": True},
            {"name": "old", "fork": False, "archived": True},
            {"name": "engine", "fork": False, "language": "Python", "stargazers_count": 4, "pushed_at": "x"},
        ]
        self.assertEqual([r["name"] for r in activity.pick_repos(repos, "LucNIK", 3, [])], ["engine"])

    def test_rss_and_atom_feeds(self) -> None:
        rss = b"""<rss><channel><item><title>Hello</title><link>https://a/1</link>
                  <pubDate>Fri, 02 Oct 2026 08:00:00 GMT</pubDate></item></channel></rss>"""
        atom = b"""<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>World</title>
                   <link href="https://a/2"/><updated>2026-10-01T10:00:00Z</updated></entry></feed>"""
        self.assertEqual(activity.parse_feed(rss, 3)[0]["title"], "Hello")
        self.assertEqual(activity.parse_feed(atom, 3)[0]["link"], "https://a/2")

    def test_relative_time(self) -> None:
        now = datetime(2026, 10, 2, 12, tzinfo=ZoneInfo("UTC"))
        self.assertEqual(activity.relative(datetime(2026, 10, 2, 11, 59, tzinfo=ZoneInfo("UTC")), now), "just now")
        self.assertEqual(activity.relative(datetime(2026, 10, 2, 9, tzinfo=ZoneInfo("UTC")), now), "3h ago")
        self.assertEqual(activity.relative(datetime(2026, 9, 1, tzinfo=ZoneInfo("UTC")), now), "Sep 1")


class FontTest(unittest.TestCase):
    def test_variable_font_is_embedded_once(self) -> None:
        from profile_engine.fonts import FontKit
        with tempfile.TemporaryDirectory() as tmp:
            for w in (400, 600, 700):
                Path(tmp, f"ibm-plex-sans-{w}.woff2").write_bytes(b"same-variable-file")
            css = FontKit("IBM Plex Sans", Path(tmp), offline=True).css((400, 600, 700))
            self.assertEqual(css.count("@font-face"), 1)
            self.assertIn("font-weight:100 900", css)


class Connect4Test(unittest.TestCase):
    def test_move_parsing_is_strict(self) -> None:
        self.assertEqual(c4.parse_move("connect4|drop|4"), 3)
        self.assertEqual(c4.parse_move(" Connect4 | DROP | 1 "), 0)
        for bad in ["connect4|drop|8", "connect4|drop|0", "connect4|drop|4; rm -rf /", "$(id)", "", None]:
            self.assertIsNone(c4.parse_move(bad))

    def test_win_detection_in_all_directions(self) -> None:
        horizontal = c4.empty_board()
        for col in range(4):
            horizontal = c4.drop(horizontal, col, c4.HUMAN)
        self.assertEqual(c4.winner(horizontal), c4.HUMAN)
        vertical = c4.empty_board()
        for _ in range(4):
            vertical = c4.drop(vertical, 6, c4.AI)
        self.assertEqual(c4.winner(vertical), c4.AI)
        diagonal = c4.empty_board()
        for col, player in [(0, 1), (1, 2), (1, 1), (2, 2), (2, 2), (2, 1), (3, 2), (3, 2), (3, 2), (3, 1)]:
            diagonal = c4.drop(diagonal, col, player)
        self.assertEqual(c4.winning_line(diagonal), [(0, 0), (1, 1), (2, 2), (3, 3)])

    def test_engine_wins_or_blocks(self) -> None:
        threat = c4.empty_board()
        for col in (0, 1, 2):
            threat = c4.drop(threat, col, c4.HUMAN)
        self.assertEqual(c4.best_move(threat, depth=4), 3)
        chance = c4.drop(c4.drop(c4.drop(threat, 6, c4.AI), 6, c4.AI), 6, c4.AI)
        self.assertEqual(c4.best_move(chance, depth=4), 6)

    def test_full_column_is_rejected(self) -> None:
        board = c4.empty_board()
        for i in range(c4.ROWS):
            board = c4.drop(board, 0, 1 + i % 2)
        with self.assertRaises(ValueError):
            c4.drop(board, 0, c4.HUMAN)


class GamePlayTest(unittest.TestCase):
    def _ctx(self, tmp: str):
        from profile_engine.context import build
        return build(load(EXAMPLE), Path(tmp), offline=True)

    def test_move_updates_board_history_and_players(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ctx = self._ctx(tmp)
            reply = game.play(ctx, "connect4|drop|4", "octo-cat")
            state = ctx.state["connect4"]
            self.assertIn("@octo-cat", reply)
            self.assertEqual(sum(len(c) for c in state["board"]), 2)  # visitor + engine
            self.assertEqual(state["players"], {"octo-cat": 1})
            self.assertEqual(state["history"][0]["col"], 4)

    def test_untrusted_inputs_never_reach_the_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ctx = self._ctx(tmp)
            reply = game.play(ctx, "connect4|drop|2", "<img src=x onerror=alert(1)>")
            self.assertNotIn("<img", reply)
            self.assertIn("@visitor", reply)
            bad = game.play(ctx, "<script>alert(1)</script>", "octo-cat")
            self.assertNotIn("<script>", bad)
            self.assertEqual(sum(len(c) for c in ctx.state["connect4"]["board"]), 2)

    def test_finished_game_restarts_on_next_move(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ctx = self._ctx(tmp)
            current = game.new_game(ctx.state)
            current.update({"over": True, "result": "ai"})
            game.play(ctx, "connect4|drop|1", "octo-cat")
            self.assertEqual(ctx.state["connect4"]["game_no"], 2)
            self.assertFalse(ctx.state["connect4"]["over"])

    def test_issue_queue_is_processed_oldest_first(self) -> None:
        issues = [
            {"number": 1, "title": "connect4|drop|4", "user": {"login": "alice"}},
            {"number": 2, "title": "Bug report", "user": {"login": "bob"}},
            {"number": 3, "title": "connect4|drop|9", "user": {"login": "carol"}},
        ]
        fake = mock.Mock()
        fake.open_issues.return_value = issues
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(game, "GitHub", return_value=fake):
            ctx = self._ctx(tmp)
            self.assertEqual(game.process_issues(ctx), 2)
        self.assertEqual([c.args[1] for c in fake.comment.call_args_list], [1, 3])
        fake.close.assert_any_call("LucNIK/LucNIK", 1, "completed")
        fake.close.assert_any_call("LucNIK/LucNIK", 3, "not_planned")

    def test_issue_link_is_prefilled(self) -> None:
        link = game.issue_link("LucNIK/LucNIK", 4)
        self.assertTrue(link.startswith("https://github.com/LucNIK/LucNIK/issues/new?title=connect4%7Cdrop%7C4"))


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
