"""Live markets card: crypto prices with 24h sparklines + Ethereum gas, refreshed every run.

Sources need no API key: CoinGecko for prices, public Ethereum JSON-RPC nodes for gas.
If a source is down, the last good snapshot is reused and marked as delayed.
"""

from __future__ import annotations

from datetime import datetime, timezone

from ..context import Context
from ..icons import icon
from ..net import FetchError, fetch_json
from ..svg import card, document, sparkline, text
from ..theme import Theme

WIDTH, HEIGHT = 840, 184
COINGECKO = "https://api.coingecko.com/api/v3"
RPC_NODES = (
    "https://ethereum-rpc.publicnode.com",
    "https://cloudflare-eth.com",
    "https://eth.llamarpc.com",
)

CURRENCY_SIGNS = {"usd": "$", "eur": "€", "gbp": "£", "cny": "¥", "jpy": "¥"}


def fetch_markets(assets: list[dict], currency: str) -> list[dict]:
    ids = ",".join(a["id"] for a in assets)
    prices = fetch_json(f"{COINGECKO}/simple/price?ids={ids}&vs_currencies={currency}"
                        f"&include_24hr_change=true")
    out = []
    for asset in assets:
        quote = prices.get(asset["id"], {})
        try:
            chart = fetch_json(f"{COINGECKO}/coins/{asset['id']}/market_chart?vs_currency={currency}&days=1")
            points = [p[1] for p in chart.get("prices", [])]
        except FetchError:
            points = []
        out.append({
            "symbol": asset["symbol"],
            "name": asset.get("name", asset["symbol"]),
            "price": quote.get(currency),
            "change": quote.get(f"{currency}_24h_change"),
            "points": _downsample(points, 48),
        })
    return out


def fetch_gas() -> dict:
    last: Exception | None = None
    for node in RPC_NODES:
        try:
            gas = fetch_json(node, payload={"jsonrpc": "2.0", "id": 1, "method": "eth_gasPrice", "params": []})
            block = fetch_json(node, payload={"jsonrpc": "2.0", "id": 2, "method": "eth_blockNumber", "params": []})
            return {"gwei": int(gas["result"], 16) / 1e9, "block": int(block["result"], 16)}
        except (FetchError, KeyError, ValueError) as exc:
            last = exc
    raise FetchError(f"all RPC nodes failed: {last}")


def _downsample(points: list[float], n: int) -> list[float]:
    if len(points) <= n:
        return points
    step = len(points) / n
    return [points[int(i * step)] for i in range(n)] + [points[-1]]


def stamp(moment: datetime) -> str:
    """'Oct 2, 14:07 UTC+8' — explicit offset instead of ambiguous zone abbreviations."""
    offset = moment.utcoffset()
    hours = offset.total_seconds() / 3600 if offset else 0
    zone = "UTC" if hours == 0 else f"UTC{hours:+g}"
    return f"{moment:%b} {moment.day}, {moment:%H:%M} {zone}"


def format_price(value: float | None, currency: str) -> str:
    if value is None:
        return "—"
    sign = CURRENCY_SIGNS.get(currency, "")
    decimals = 0 if value >= 1000 else 2 if value >= 1 else 4
    return f"{sign}{value:,.{decimals}f}"


def format_change(value: float | None) -> str:
    if value is None:
        return "—"
    return f"{'▲' if value >= 0 else '▼'} {abs(value):.2f}%"


def render_theme(ctx: Context, theme: Theme, data: dict) -> str:
    markets, gas = data.get("markets", []), data.get("gas")
    currency = ctx.config.ticker_currency
    columns = len(markets) + (1 if gas else 0)
    pad, gap = 24, 16
    col_w = (WIDTH - 2 * pad - gap * (columns - 1)) / max(columns, 1)

    updated = datetime.fromisoformat(data["updated"]).astimezone(ctx.now.tzinfo)
    status = "LIVE" if not data.get("stale") else "DELAYED"
    body = [
        card(1, 1, WIDTH - 2, HEIGHT - 2, theme, r=14),
        f'<circle cx="{pad + 4}" cy="31" r="4" fill="{theme.up if status == "LIVE" else theme.muted}">'
        + ('<animate attributeName="opacity" values="1;.25;1" dur="2s" repeatCount="indefinite"/>'
           if status == "LIVE" else "") + "</circle>",
        text(pad + 16, 35.5, f"MARKETS · {status}", size=12, fill=theme.text, weight=600, spacing=2.5),
        text(WIDTH - pad, 35.5, f"Updated {stamp(updated)}", size=11.5, fill=theme.muted, anchor="end"),
        f'<path d="M{pad} 52H{WIDTH - pad}" stroke="{theme.grid}"/>',
    ]
    for i, m in enumerate(markets):
        x = pad + i * (col_w + gap)
        change = m.get("change")
        tone = theme.up if (change or 0) >= 0 else theme.down
        body += [
            icon("coin" if m["symbol"] == "BTC" else "ethereum" if m["symbol"] == "ETH" else "coin",
                 x, 66, 18, theme.accent),
            text(x + 26, 80, m["symbol"], size=13, fill=theme.text, weight=600, spacing=1.5),
            text(x + 26 + 10 * len(m["symbol"]) + 4, 80, m["name"], size=12, fill=theme.muted),
            text(x, 112, format_price(m.get("price"), currency), size=24, fill=theme.text, weight=600),
            text(x + col_w, 80, format_change(change), size=12, fill=tone, weight=600, anchor="end"),
            sparkline(m.get("points", []), x, 126, col_w, 34, stroke=tone, fill_id=f"sp{i}{theme.name}"),
        ]
    if gas:
        x = pad + len(markets) * (col_w + gap)
        gwei = gas["gwei"]
        level, tone = (("LOW", theme.up) if gwei < 5 else ("MODERATE", theme.accent) if gwei < 25
                       else ("HIGH", theme.down))
        body += [
            icon("gas", x, 66, 18, theme.accent),
            text(x + 26, 80, "GAS", size=13, fill=theme.text, weight=600, spacing=1.5),
            text(x + 26 + 36, 80, "Ethereum", size=12, fill=theme.muted),
            text(x, 112, f"{gwei:.2f} gwei" if gwei < 10 else f"{gwei:.1f} gwei", size=24, fill=theme.text,
                 weight=600),
            text(x + col_w, 80, level, size=12, fill=tone, weight=600, anchor="end", spacing=1),
            f'<rect x="{x}" y="132" width="{col_w}" height="6" rx="3" fill="{theme.grid}"/>',
            f'<rect x="{x}" y="132" width="{col_w * min(gwei / 50, 1):.1f}" height="6" rx="3" fill="{tone}"/>',
            text(x, 158, f"Block #{gas['block']:,}", size=11.5, fill=theme.muted, mono=True),
        ]
    title = "Markets: " + ", ".join(f"{m['symbol']} {format_price(m.get('price'), currency)}" for m in markets)
    return document(WIDTH, HEIGHT, "".join(body), title=title, fonts=ctx.fonts, weights=(400, 600))


def collect(ctx: Context) -> dict:
    cfg = ctx.config
    previous = ctx.state.get("ticker")
    if ctx.offline:
        return previous or sample_data(ctx)
    data: dict = {"updated": datetime.now(timezone.utc).isoformat(), "stale": False}
    try:
        data["markets"] = fetch_markets(cfg.ticker_assets, cfg.ticker_currency)
    except FetchError as exc:
        print(f"[ticker] markets: {exc}")
        if previous:
            return {**previous, "stale": True}
        # First run and no source reachable: draw the card with placeholders rather than nothing.
        data["stale"] = True
        data["markets"] = [{"symbol": a["symbol"], "name": a.get("name", a["symbol"]), "price": None,
                            "change": None, "points": []} for a in cfg.ticker_assets]
    if cfg.ticker_gas:
        try:
            data["gas"] = fetch_gas()
        except FetchError as exc:
            print(f"[ticker] gas: {exc}")
            data["gas"] = (previous or {}).get("gas")
    return data


def sample_data(ctx: Context) -> dict:
    import math
    wave = lambda base, amp, k: [base + amp * math.sin(i / k) + amp * 0.4 * math.sin(i / 2.3) for i in range(48)]
    return {
        "updated": ctx.now.isoformat(), "stale": False,
        "markets": [
            {"symbol": "BTC", "name": "Bitcoin", "price": 64250.0, "change": 2.41, "points": wave(64000, 600, 6)},
            {"symbol": "ETH", "name": "Ethereum", "price": 3120.55, "change": -1.18,
             "points": wave(3150, 40, 5)[::-1]},
        ],
        "gas": {"gwei": 7.42, "block": 23_481_337},
    }


def render(ctx: Context) -> None:
    data = collect(ctx)
    ctx.state["ticker"] = data
    for theme in ctx.themes:
        ctx.write(f"ticker-{theme.name}.svg", render_theme(ctx, theme, data))
