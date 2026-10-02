<!-- Copyright (c) 2026 John Luke NIKABOU (LucNIK) — MIT License -->
<div align="center">

# NIK Profile Engine

**A self-hosted GitHub Action that renders a living, day/night themed GitHub profile.**
Animated hero · Connect Four vs an AI, played through issues · activity feed · live crypto & gas ticker · weekly AI summary · zero external image services.

[Live demo → github.com/LucNIK](https://github.com/LucNIK) · [Configuration](#configuration) · [Modules](#modules)

</div>

---

## Why

Most profile READMEs stitch together third-party image services. They rate-limit, go down, and look like everyone
else's. **profile-engine** renders every visual itself, inside your own workflow, from live data — and publishes the
result to a branch of your profile repository. Nothing on your profile depends on someone else's server at view time.

- **Day & night.** Every visual is rendered twice and swapped with `prefers-color-scheme`.
- **Self-contained SVGs.** Fonts are embedded as base64 and icons are hand-drawn paths, so images never load external
  resources — exactly what GitHub's image proxy requires.
- **Live data.** Market prices with 24h sparklines (CoinGecko), Ethereum gas from public JSON-RPC nodes, followers
  from the GitHub API.
- **AI, without secrets.** The weekly summary uses **GitHub Models** with the workflow's own token — no API key to
  manage — and falls back to a deterministic summary if the model is unavailable.
- **Resilient by design.** Each module is isolated: one failing source never breaks the others, and the last good
  snapshot is reused (marked *delayed*) when an API is down.
- **Accessible.** Every SVG has `role="img"` and a descriptive `<title>`; animations respect `prefers-reduced-motion`.
- **Zero dependencies.** Pure Python standard library.

## Architecture

```mermaid
flowchart LR
    T[profile.toml] --> E{{profile-engine}}
    GH[(GitHub API)] --> E
    CG[(CoinGecko)] --> E
    RPC[(Ethereum RPC)] --> E
    GM[(GitHub Models)] --> E
    RSS[(RSS / Atom)] --> E
    E -->|hero · headings · focus · badges · activity · ticker · weekly| S[light + dark SVGs]
    S --> O[output branch]
    O --> R[README via &lt;picture&gt;]
```

## Usage

```yaml
# .github/workflows/profile.yml
name: Profile
on:
  schedule:
    - cron: "7 * * * *"   # hourly: markets ticker
  workflow_dispatch:

permissions:
  contents: write   # publish the SVGs
  models: read      # weekly AI summary via GitHub Models

jobs:
  render:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Restore previous output (keeps engine state and caches)
        run: |
          mkdir -p dist
          git fetch --depth=1 origin output && git archive FETCH_HEAD | tar -x -C dist || true

      - uses: LucNIK/profile-engine@v1
        with:
          config: profile.toml
          output_dir: dist

      - uses: crazy-max/ghaction-github-pages@v4
        with:
          target_branch: output
          build_dir: dist
          jekyll: false
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

Then reference the images in your README, one `<picture>` per visual:

```html
<picture>
  <source media="(prefers-color-scheme: dark)"  srcset="https://raw.githubusercontent.com/USER/USER/output/ticker-dark.svg">
  <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/USER/USER/output/ticker-light.svg">
  <img alt="Live markets" src="https://raw.githubusercontent.com/USER/USER/output/ticker-light.svg">
</picture>
```

### Inputs

| Input | Default | Description |
| --- | --- | --- |
| `config` | `profile.toml` | Path to the configuration file |
| `output_dir` | `dist` | Where SVGs and `engine-state.json` are written |
| `modules` | `all` | Subset: `hero, headings, focus, badges, activity, game, ticker, weekly` |
| `game_process_issues` | `false` | `true` plays every open move issue, replies and closes it |
| `game_move` / `game_player` | — | Play a single move directly (testing) |
| `github_token` | `github.token` | GitHub API + GitHub Models token |
| `python_version` | `3.12` | Python used to run the engine |

## Connect Four, played through issues

Visitors click a column button in your README. That opens a pre-filled issue titled `connect4|drop|<n>`;
a workflow plays every open move issue in order (so simultaneous players never lose a move), the engine answers with **minimax + alpha-beta pruning** (6 plies by default),
the board is re-rendered, and the issue gets a reply and is closed.

```yaml
# .github/workflows/game.yml
name: Connect Four
on:
  issues:
    types: [opened]
permissions:
  contents: write   # publish the new board
  issues: write     # reply to and close move issues
concurrency:
  group: profile    # same group as the profile workflow: one writer at a time
  cancel-in-progress: false
jobs:
  move:
    if: startsWith(github.event.issue.title, 'connect4')
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: |
          mkdir -p dist
          git fetch --depth=1 origin output && git archive FETCH_HEAD | tar -x -C dist || true
      - uses: LucNIK/profile-engine@v1
        with:
          modules: game
          game_process_issues: "true"   # plays every open move issue, replies and closes it
      - uses: crazy-max/ghaction-github-pages@v4
        with: { target_branch: output, build_dir: dist, jekyll: false }
        env: { GITHUB_TOKEN: "${{ secrets.GITHUB_TOKEN }}" }
```

Each column button links to `https://github.com/USER/USER/issues/new?title=connect4%7Cdrop%7C<n>`.
Untrusted input is handled defensively: the title must match a strict pattern, player names are validated,
and neither ever reaches a shell or the rendered images unchecked.

## Modules

| Module | Output | Refresh |
| --- | --- | --- |
| `hero` | `hero-{light,dark}.svg` — typewriter title, pure CSS | on every run |
| `headings` | `heading-<slug>-{light,dark}.svg` — numbered section titles | on every run |
| `focus` | `focus-{light,dark}.svg` — icon cards | on every run |
| `badges` | `badge-website-*`, `badge-followers-*` | on every run |
| `game` | `game-{light,dark}.svg`, `game-col-<1-7>-{light,dark}.svg` — Connect Four vs a minimax AI | every run / every move |
| `activity` | `activity-{light,dark}.svg` — recent projects, latest public events, optional RSS posts | on every run |
| `ticker` | `ticker-{light,dark}.svg` — prices, 24h change, sparklines, gas | every run (hourly) |
| `weekly` | `weekly-{light,dark}.svg` — AI summary of the last 7 days of commits | once per ISO week |

## Configuration

See [`examples/profile.toml`](examples/profile.toml) for a complete file.

```toml
[profile]
user = "LucNIK"
name = "Luc NIK"
website = "https://ayuefu.com"
timezone = "Asia/Shanghai"

[theme]
font = "IBM Plex Sans"      # any Google Font
light_accent = "#B7860B"    # day
dark_accent = "#C1121F"     # night

[hero]
lines = ["Luc NIK", "Software Engineer", "AI/ML · FinTech · Web3"]

[headings]
titles = ["About", "Focus", "Markets", "This Week"]

[[focus.items]]
title = "AI / ML"
lines = ["Models · data pipelines", "intelligent applications"]
icon = "network"            # network, candles, ethereum, cloud, gas, spark, globe, users, coin

[activity]
repos = 3
events = 5
rss = ""                    # optional: "https://example.com/rss.xml"

[game]
repo = "LucNIK/LucNIK"      # where move issues are opened
depth = 6                   # engine strength (1-8)

[ticker]
currency = "usd"
gas = true
assets = [{ id = "bitcoin", symbol = "BTC", name = "Bitcoin" }]

[weekly]
model = "openai/gpt-4.1-mini"
exclude_repos = []
```

## Local preview & tests

```bash
python -m profile_engine --config examples/profile.toml --out dist --offline   # sample data, no network
python -m unittest -v
```

## Changelog

- **1.2.0** — `game` module: Connect Four against a minimax AI, played by visitors through issues; GitHub Models
  call hardened (redirect and non-JSON detection, fallback endpoint); action inputs passed via environment only.
- **1.1.0** — `activity` module (recent projects, public events, RSS/Atom posts); variable fonts embedded once
  (≈50% lighter SVGs); detailed GitHub Models errors stored in the engine state, with an automatic retry every 6 hours.
- **1.0.0** — first release: hero, headings, focus, badges, ticker, weekly AI summary.

## License

[MIT](LICENSE) © John Luke NIKABOU
