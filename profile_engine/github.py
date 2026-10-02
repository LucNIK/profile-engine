"""Minimal GitHub REST client."""

from __future__ import annotations

from urllib.parse import quote

from .net import fetch_json

API = "https://api.github.com"


class GitHub:
    def __init__(self, token: str = "") -> None:
        self.headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
        if token:
            self.headers["Authorization"] = f"Bearer {token}"

    def user(self, login: str) -> dict:
        return fetch_json(f"{API}/users/{quote(login)}", headers=self.headers)

    def commits_since(self, login: str, since_date: str, limit: int = 200) -> list[dict]:
        """Commits authored by `login` since YYYY-MM-DD, newest first (default branches only)."""
        query = quote(f"author:{login} author-date:>={since_date}")
        results: list[dict] = []
        page = 1
        while len(results) < limit:
            data = fetch_json(
                f"{API}/search/commits?q={query}&sort=author-date&order=desc&per_page=100&page={page}",
                headers=self.headers,
            )
            items = data.get("items", [])
            results.extend(items)
            if len(items) < 100:
                break
            page += 1
        return [
            {
                "repo": item["repository"]["full_name"],
                "message": item["commit"]["message"].splitlines()[0][:140],
                "date": item["commit"]["author"]["date"],
            }
            for item in results[:limit]
            if len(item.get("parents", [])) <= 1  # skip merge commits
        ]
