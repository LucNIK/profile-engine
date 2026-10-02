# SPDX-License-Identifier: MIT
# Copyright (c) 2026 John Luke NIKABOU (LucNIK)

"""Activity feed: recent projects, latest public GitHub activity and (optionally) latest articles from an RSS/Atom feed."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

from ..context import Context
from ..github import GitHub
from ..icons import icon
from ..net import FetchError, fetch
from ..svg import card, document, text, text_width
from ..theme import Theme

WIDTH, PAD, GAP = 840, 28, 28
COL_W = (WIDTH - 2 * PAD - GAP) / 2
REPO_ROW, EVENT_ROW, POST_ROW = 72, 32, 30

LANGUAGE_COLORS = {
    "Python": "#3572A5", "TypeScript": "#3178C6", "JavaScript": "#F1E05A", "Solidity": "#AA6746",
    "Go": "#00ADD8", "Rust": "#DEA584", "Java": "#B07219", "HTML": "#E34C26", "CSS": "#663399",
    "Shell": "#89E051", "Jupyter Notebook": "#DA5B0B", "C++": "#F34B7D", "C": "#555555",
    "Kotlin": "#A97BFF", "Swift": "#F05138", "Dart": "#00B4AB", "PHP": "#4F5D95", "Ruby": "#701516",
}


# ---------------------------------------------------------------- data

def relative(moment: datetime, now: datetime) -> str:
    seconds = (now - moment).total_seconds()
    if seconds < 90:
        return "just now"
    if seconds < 3600:
        return f"{int(seconds // 60)}m ago"
    if seconds < 86400:
        return f"{int(seconds // 3600)}h ago"
    if seconds < 86400 * 7:
        return f"{int(seconds // 86400)}d ago"
    return f"{moment:%b} {moment.day}"


def _short(repo: str, user: str) -> str:
    owner, _, name = repo.partition("/")
    return name if owner.lower() == user.lower() else repo


def describe(event: dict, user: str) -> str | None:
    """Human sentence for a GitHub event, or None for events not worth showing."""
    kind, payload = event.get("type"), event.get("payload") or {}
    repo = _short(event.get("repo", {}).get("name", ""), user)
    if kind == "PushEvent":
        n = payload.get("size") or len(payload.get("commits") or [])
        return f"Pushed {n} commit{'s' if n != 1 else ''} to {repo}" if n else f"Pushed to {repo}"
    if kind == "PullRequestEvent":
        pr = payload.get("pull_request") or {}
        number = pr.get("number") or payload.get("number")
        if payload.get("action") == "closed" and pr.get("merged"):
            return f"Merged PR #{number} in {repo}"
        if payload.get("action") == "opened":
            return f"Opened PR #{number} in {repo}"
        return None
    if kind == "CreateEvent":
        if payload.get("ref_type") == "repository":
            return f"Created {repo}"
        if payload.get("ref_type") == "tag":
            return f"Tagged {payload.get('ref')} in {repo}"
        return None
    if kind == "ReleaseEvent":
        return f"Released {(payload.get('release') or {}).get('tag_name', 'a new version')} of {repo}"
    if kind == "PublicEvent":
        return f"Open-sourced {repo}"
    if kind == "WatchEvent":
        return f"Starred {repo}"
    if kind == "ForkEvent":
        return f"Forked {repo}"
    if kind == "IssuesEvent" and payload.get("action") == "opened":
        return f"Opened issue #{(payload.get('issue') or {}).get('number')} in {repo}"
    return None


def summarize_events(events: list[dict], user: str, limit: int) -> list[dict]:
    """Describe events, merging consecutive pushes to the same repository."""
    out: list[dict] = []
    for event in events:
        sentence = describe(event, user)
        if not sentence:
            continue
        repo = event.get("repo", {}).get("name", "")
        if (event.get("type") == "PushEvent" and out and out[-1]["type"] == "PushEvent"
                and out[-1]["repo"] == repo):
            prev = out[-1]
            prev["count"] += (event.get("payload") or {}).get("size") or 0
            n = prev["count"]
            if n:
                prev["text"] = f"Pushed {n} commit{'s' if n != 1 else ''} to {_short(repo, user)}"
            continue
        out.append({
            "type": event.get("type"), "repo": repo, "text": sentence, "at": event.get("created_at"),
            "count": (event.get("payload") or {}).get("size") or 0,
        })
        if len(out) >= limit:
            break
    return [{"text": e["text"], "at": e["at"]} for e in out]


def pick_repos(repos: list[dict], user: str, limit: int, exclude: list[str]) -> list[dict]:
    skip = {n.lower() for n in exclude} | {user.lower()}
    picked = []
    for r in repos:
        if r.get("fork") or r.get("archived") or r.get("private") or r["name"].lower() in skip:
            continue
        picked.append({
            "name": r["name"], "description": r.get("description") or "", "language": r.get("language"),
            "stars": r.get("stargazers_count", 0), "pushed": r.get("pushed_at"),
        })
        if len(picked) >= limit:
            break
    return picked


def parse_feed(xml_bytes: bytes, limit: int) -> list[dict]:
    """Read the newest posts from an RSS 2.0 or Atom feed."""
    root = ET.fromstring(xml_bytes)
    atom = "{http://www.w3.org/2005/Atom}"
    posts = []
    for item in root.iter("item"):  # RSS
        date = item.findtext("pubDate")
        posts.append({
            "title": (item.findtext("title") or "").strip(), "link": (item.findtext("link") or "").strip(),
            "at": parsedate_to_datetime(date).isoformat() if date else None,
        })
    for entry in root.iter(f"{atom}entry"):  # Atom
        link = entry.find(f"{atom}link")
        posts.append({
            "title": (entry.findtext(f"{atom}title") or "").strip(),
            "link": link.get("href", "") if link is not None else "",
            "at": entry.findtext(f"{atom}updated") or entry.findtext(f"{atom}published"),
        })
    return [p for p in posts if p["title"]][:limit]


def collect(ctx: Context) -> dict:
    cfg, previous = ctx.config, ctx.state.get("activity")
    if ctx.offline:
        return previous or sample_data(ctx)
    gh = GitHub(ctx.token)
    data = {"repos": [], "events": [], "posts": []}
    try:
        data["repos"] = pick_repos(gh.repos(cfg.user), cfg.user, cfg.activity_repos, cfg.activity_exclude)
        data["events"] = summarize_events(gh.events(cfg.user), cfg.user, cfg.activity_events)
    except FetchError as exc:
        print(f"[activity] github: {exc}")
        if previous:
            return previous
    if cfg.activity_rss:
        try:
            data["posts"] = parse_feed(fetch(cfg.activity_rss), cfg.activity_posts)
        except (FetchError, ET.ParseError) as exc:
            print(f"[activity] rss: {exc}")
            data["posts"] = (previous or {}).get("posts", [])
    return data


def sample_data(ctx: Context) -> dict:
    now = ctx.now.astimezone(timezone.utc)
    ago = lambda h: now.replace(microsecond=0).timestamp() - h * 3600
    iso = lambda h: datetime.fromtimestamp(ago(h), timezone.utc).isoformat()
    return {
        "repos": [
            {"name": "profile-engine", "description": "Self-hosted GitHub Action rendering a living, themed profile",
             "language": "Python", "stars": 12, "pushed": iso(2)},
            {"name": "defi-signals", "description": "Volatility models and trading signals for on-chain markets",
             "language": "TypeScript", "stars": 7, "pushed": iso(30)},
            {"name": "ayuefu", "description": "Personal website and engineering notes",
             "language": "TypeScript", "stars": 3, "pushed": iso(80)},
        ],
        "events": [
            {"text": "Pushed 4 commits to profile-engine", "at": iso(2)},
            {"text": "Released v1.1.0 of profile-engine", "at": iso(3)},
            {"text": "Merged PR #12 in defi-signals", "at": iso(26)},
            {"text": "Created ayuefu-api", "at": iso(50)},
            {"text": "Starred ethereum/go-ethereum", "at": iso(70)},
        ],
        "posts": [],
    }


# ---------------------------------------------------------------- render

def ellipsize(value: str, size: float, max_width: float, weight: int = 400) -> str:
    if text_width(value, size, weight) <= max_width:
        return value
    while value and text_width(value + "…", size, weight) > max_width:
        value = value[:-1]
    return value.rstrip() + "…"


def _when(iso: str | None, ctx: Context) -> str:
    if not iso:
        return ""
    return relative(datetime.fromisoformat(iso.replace("Z", "+00:00")), ctx.now)


def render_theme(ctx: Context, theme: Theme, data: dict) -> str:
    repos, events, posts = data.get("repos", []), data.get("events", []), data.get("posts", [])
    body_h = max(len(repos) * REPO_ROW, len(events) * EVENT_ROW, 40)
    posts_h = (44 + len(posts) * POST_ROW) if posts else 0
    height = 70 + body_h + posts_h + 16
    left, right = PAD, PAD + COL_W + GAP

    out = [
        card(1, 1, WIDTH - 2, height - 2, theme, r=14),
        text(left, 38, "RECENT PROJECTS", size=12, fill=theme.text, weight=600, spacing=2.5),
        text(right, 38, "LATEST ACTIVITY", size=12, fill=theme.text, weight=600, spacing=2.5),
        f'<path d="M{PAD} 54H{WIDTH - PAD}" stroke="{theme.grid}"/>',
        f'<path d="M{right - GAP / 2} 66V{70 + body_h - 8}" stroke="{theme.grid}"/>',
    ]
    for i, repo in enumerate(repos):
        y = 82 + i * REPO_ROW
        out.append(text(left, y, ellipsize(repo["name"], 14.5, COL_W, 600), size=14.5, fill=theme.accent,
                        weight=600))
        if repo["description"]:
            out.append(text(left, y + 19, ellipsize(repo["description"], 12.5, COL_W), size=12.5,
                            fill=theme.muted))
        meta_x = left
        if repo.get("language"):
            out.append(f'<circle cx="{meta_x + 5}" cy="{y + 36}" r="5" '
                       f'fill="{LANGUAGE_COLORS.get(repo["language"], theme.muted)}"/>')
            out.append(text(meta_x + 15, y + 40, repo["language"], size=11.5, fill=theme.text))
            meta_x += 15 + text_width(repo["language"], 11.5) + 16
        out.append(text(meta_x, y + 40, f"★ {repo['stars']}", size=11.5, fill=theme.text))
        meta_x += text_width(f"★ {repo['stars']}", 11.5) + 16
        out.append(text(meta_x, y + 40, f"updated {_when(repo.get('pushed'), ctx)}", size=11.5,
                        fill=theme.muted))
    if not repos:
        out.append(text(left, 88, "No public projects yet", size=12.5, fill=theme.muted))

    for i, event in enumerate(events):
        y = 84 + i * EVENT_ROW
        when = _when(event.get("at"), ctx)
        when_w = text_width(when, 11.5) + 10
        out.append(f'<circle cx="{right + 4}" cy="{y - 4}" r="3.5" fill="none" stroke="{theme.accent}" '
                   f'stroke-width="1.5"/>')
        if i < len(events) - 1:
            out.append(f'<path d="M{right + 4} {y + 1}V{y + EVENT_ROW - 9}" stroke="{theme.grid}" '
                       f'stroke-width="1.5"/>')
        out.append(text(right + 16, y, ellipsize(event["text"], 13, COL_W - 16 - when_w), size=13,
                        fill=theme.text))
        out.append(text(right + COL_W, y, when, size=11.5, fill=theme.muted, anchor="end"))
    if not events:
        out.append(text(right, 88, "No recent public activity", size=12.5, fill=theme.muted))

    if posts:
        y0 = 70 + body_h + 8
        out.append(f'<path d="M{PAD} {y0}H{WIDTH - PAD}" stroke="{theme.grid}"/>')
        out.append(icon("spark", left, y0 + 14, 16, theme.accent))
        out.append(text(left + 24, y0 + 27, "LATEST ARTICLES", size=12, fill=theme.text, weight=600,
                        spacing=2.5))
        for i, post in enumerate(posts):
            y = y0 + 58 + i * POST_ROW
            when = _when(post.get("at"), ctx)
            out.append(text(left, y, ellipsize(post["title"], 13.5, WIDTH - 2 * PAD - 90), size=13.5,
                            fill=theme.text))
            out.append(text(WIDTH - PAD, y, when, size=11.5, fill=theme.muted, anchor="end"))

    title = "Activity: " + "; ".join([r["name"] for r in repos] + [e["text"] for e in events[:3]])
    return document(WIDTH, height, "".join(out), title=title, fonts=ctx.fonts, weights=(400, 600))


def render(ctx: Context) -> None:
    if not ctx.config.activity_enabled:
        return
    data = collect(ctx)
    ctx.state["activity"] = data
    for theme in ctx.themes:
        ctx.write(f"activity-{theme.name}.svg", render_theme(ctx, theme, data))
