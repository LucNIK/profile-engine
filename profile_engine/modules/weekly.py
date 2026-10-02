"""Weekly AI summary: reads the week's commits and asks a language model to write
"What I built this week" in the first person.

Runs once per ISO week (cached in the engine state), uses GitHub Models with the workflow's own
token (no extra secret), and falls back to a deterministic summary if the model is unavailable.
"""

from __future__ import annotations

import os
from collections import Counter
from datetime import date, timedelta

from ..context import Context
from ..github import GitHub
from ..icons import icon
from ..net import FetchError, fetch_json
from ..svg import card, document, text, text_width, wrap
from ..theme import Theme

MODELS_ENDPOINT = "https://models.github.ai/inference/chat/completions"
WIDTH = 840
PAD = 28
BODY_SIZE = 15
LINE_H = 23

SYSTEM_PROMPT = (
    "You write the weekly section of a software engineer's GitHub profile. "
    "From the commit list, write what they built this week in the first person: "
    "2 to 3 sentences, at most 60 words, concrete and specific, naming projects. "
    "No hype words, no emojis, no hashtags, no bullet points, no preamble."
)


def week_key(ctx: Context) -> str:
    year, week, _ = ctx.now.isocalendar()
    return f"{year}-W{week:02d}"


def stats_for(commits: list[dict]) -> dict:
    repos = Counter(c["repo"].split("/")[-1] for c in commits)
    return {"commits": len(commits), "repos": len(repos), "top": [r for r, _ in repos.most_common(3)]}


def fallback_summary(stats: dict) -> str:
    if not stats["commits"]:
        return ("A quieter week on public repositories — time spent on research, design and work "
                "that ships later. New commits will show up here automatically.")
    top = stats["top"]
    where = top[0] if len(top) == 1 else ", ".join(top[:-1]) + f" and {top[-1]}"
    plural = "y" if stats["repos"] == 1 else "ies"
    noun = "commit" if stats["commits"] == 1 else "commits"
    return (f"I shipped {stats['commits']} {noun} across {stats['repos']} repositor{plural} this week, "
            f"with most of the work landing in {where}.")


def ask_model(model: str, token: str, commits: list[dict]) -> str:
    listing = "\n".join(f"- [{c['repo'].split('/')[-1]}] {c['message']}" for c in commits[:80])
    response = fetch_json(
        MODELS_ENDPOINT,
        payload={
            "model": model,
            "temperature": 0.4,
            "max_tokens": 160,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Commits from the last 7 days:\n{listing}"},
            ],
        },
        headers={"Authorization": f"Bearer {token}"},
        timeout=40,
        retries=1,
    )
    content = response["choices"][0]["message"]["content"].strip().strip('"')
    if not content:
        raise ValueError("empty model response")
    return content


def collect(ctx: Context) -> dict:
    cfg = ctx.config
    key = week_key(ctx)
    cached = ctx.state.get("weekly")
    if cached and cached.get("week") == key and not os.environ.get("FORCE_WEEKLY"):
        return cached
    start = ctx.now - timedelta(days=7)
    if ctx.offline:
        commits = sample_commits()
    else:
        try:
            commits = GitHub(ctx.token).commits_since(cfg.user, start.date().isoformat())
        except FetchError as exc:
            print(f"[weekly] commits: {exc}")
            if cached:
                return cached
            commits = []
    commits = [c for c in commits if c["repo"].split("/")[-1] not in cfg.weekly_exclude_repos]
    stats = stats_for(commits)
    summary, source = fallback_summary(stats), "auto"
    if commits and ctx.token and not ctx.offline:
        try:
            summary, source = ask_model(cfg.weekly_model, ctx.token, commits), cfg.weekly_model
        except (FetchError, KeyError, IndexError, ValueError) as exc:
            print(f"[weekly] model: {exc} — using deterministic summary")
    return {
        "week": key,
        "range": [start.date().isoformat(), ctx.now.date().isoformat()],
        "summary": summary,
        "source": source,
        **stats,
    }


def sample_commits() -> list[dict]:
    rows = [
        ("LucNIK/profile-engine", "Add live markets ticker with gas oracle"),
        ("LucNIK/profile-engine", "Render day/night SVG themes with embedded fonts"),
        ("LucNIK/LucNIK", "Wire profile to the engine"),
        ("LucNIK/defi-signals", "Train volatility model on hourly candles"),
    ]
    return [{"repo": r, "message": m, "date": ""} for r, m in rows]


def render_theme(ctx: Context, theme: Theme, data: dict) -> str:
    lines = wrap(data["summary"], BODY_SIZE, WIDTH - 2 * PAD)
    chips_y = 96 + len(lines) * LINE_H
    height = chips_y + 50
    d0, d1 = (date.fromisoformat(d) for d in data["range"])
    span = f"{d0:%b} {d0.day} – {d1:%b} {d1.day}"
    body = [
        card(1, 1, WIDTH - 2, height - 2, theme, r=14),
        icon("spark", PAD, 22, 20, theme.accent),
        text(PAD + 30, 37, "THIS WEEK", size=12, fill=theme.text, weight=600, spacing=2.5),
        text(PAD + 30 + text_width("THIS WEEK", 12, 600, 2.5) + 12, 37, span, size=12, fill=theme.muted),
        text(WIDTH - PAD, 37, f"{data['commits']} commits · {data['repos']} repos", size=12,
             fill=theme.muted, anchor="end"),
        f'<path d="M{PAD} 56H{WIDTH - PAD}" stroke="{theme.grid}"/>',
    ]
    for i, line in enumerate(lines):
        body.append(text(PAD, 86 + i * LINE_H, line, size=BODY_SIZE, fill=theme.text))
    x = PAD
    for repo in data.get("top", []):
        w = text_width(repo, 11.5, 600, 0.3) + 22
        body.append(f'<rect x="{x}" y="{chips_y}" width="{w:.1f}" height="24" rx="12" fill="none" '
                    f'stroke="{theme.accent}" stroke-opacity=".6"/>')
        body.append(text(x + 11, chips_y + 16, repo, size=11.5, fill=theme.accent, weight=600, spacing=0.3))
        x += w + 8
    credit = "Written by AI · " + data["source"] if data["source"] != "auto" else "Auto-generated from commits"
    body.append(text(WIDTH - PAD, chips_y + 16, credit, size=11, fill=theme.muted, anchor="end"))
    return document(WIDTH, height, "".join(body), title=f"This week: {data['summary']}",
                    fonts=ctx.fonts, weights=(400, 600))


def render(ctx: Context) -> None:
    if not ctx.config.weekly_enabled:
        return
    data = collect(ctx)
    ctx.state["weekly"] = data
    for theme in ctx.themes:
        ctx.write(f"weekly-{theme.name}.svg", render_theme(ctx, theme, data))
