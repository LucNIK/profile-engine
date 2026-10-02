# SPDX-License-Identifier: MIT
# Copyright (c) 2026 John Luke NIKABOU (LucNIK)

"""Tiny HTTP layer on the standard library: timeouts, retries, JSON."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Any

USER_AGENT = "profile-engine/1.2 (+https://github.com/LucNIK/profile-engine)"


class FetchError(RuntimeError):
    pass


def fetch(url: str, *, data: bytes | None = None, headers: dict[str, str] | None = None,
          timeout: float = 15.0, retries: int = 2, method: str | None = None) -> bytes:
    hdrs = {"User-Agent": USER_AGENT, **(headers or {})}
    last: Exception | None = None
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, data=data, headers=hdrs, method=method or ("POST" if data else "GET"))
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = resp.read()
                if data is not None and resp.geturl() != url:
                    # urllib turns a redirected POST into a body-less GET: surface it instead of
                    # failing later on an unexpected response.
                    raise FetchError(f"{url}: POST redirected to {resp.geturl()}")
                return body
        except urllib.error.HTTPError as exc:  # 4xx are not worth retrying, except rate limits
            detail = exc.read()[:300].decode("utf-8", "replace").strip()
            last = RuntimeError(f"HTTP {exc.code} {exc.reason}" + (f" — {detail}" if detail else ""))
            if exc.code < 500 and exc.code != 429:
                break
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last = exc
        if attempt < retries:
            time.sleep(1.5 * (attempt + 1))
    raise FetchError(f"{url}: {last}")


def fetch_json(url: str, *, payload: Any = None, headers: dict[str, str] | None = None,
               timeout: float = 15.0, retries: int = 2, method: str | None = None) -> Any:
    hdrs = {"Accept": "application/json", **(headers or {})}
    data = None
    if payload is not None:
        data = json.dumps(payload).encode()
        hdrs["Content-Type"] = "application/json"
    body = fetch(url, data=data, headers=hdrs, timeout=timeout, retries=retries, method=method)
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        preview = body[:160].decode("utf-8", "replace").strip() or "<empty body>"
        raise FetchError(f"{url}: expected JSON, got {len(body)} bytes: {preview}") from None
