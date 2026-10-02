"""Tiny HTTP layer on the standard library: timeouts, retries, JSON."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Any

USER_AGENT = "profile-engine/1.0 (+https://github.com/LucNIK/profile-engine)"


class FetchError(RuntimeError):
    pass


def fetch(url: str, *, data: bytes | None = None, headers: dict[str, str] | None = None,
          timeout: float = 15.0, retries: int = 2) -> bytes:
    hdrs = {"User-Agent": USER_AGENT, **(headers or {})}
    last: Exception | None = None
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, data=data, headers=hdrs, method="POST" if data else "GET")
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except urllib.error.HTTPError as exc:  # 4xx are not worth retrying, except rate limits
            last = exc
            if exc.code < 500 and exc.code != 429:
                break
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last = exc
        if attempt < retries:
            time.sleep(1.5 * (attempt + 1))
    raise FetchError(f"{url}: {last}")


def fetch_json(url: str, *, payload: Any = None, headers: dict[str, str] | None = None,
               timeout: float = 15.0, retries: int = 2) -> Any:
    hdrs = {"Accept": "application/json", **(headers or {})}
    data = None
    if payload is not None:
        data = json.dumps(payload).encode()
        hdrs["Content-Type"] = "application/json"
    return json.loads(fetch(url, data=data, headers=hdrs, timeout=timeout, retries=retries))
