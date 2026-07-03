"""Multi-athlete name→ID resolution fetched from Intervals.icu API at startup.

Fetches all athletes tagged "Coaching" from /api/v1/athletes using the
coach's own API key. No athletes.json required.
"""

from __future__ import annotations

import httpx

from .auth import load_config

_cache: dict[str, str] | None = None  # {firstname_lower: athlete_id}
_cache_full: list[dict[str, str]] | None = None  # [{name, id}]


def _fetch() -> list[dict[str, str]]:
    """Fetch coached athletes from API. Returns list of {name, id}."""
    config = load_config()
    auth = httpx.BasicAuth(username="API_KEY", password=config.intervals_icu_api_key)

    with httpx.Client(auth=auth, timeout=10.0) as client:
        response = client.get("https://intervals.icu/api/v1/athletes")
        response.raise_for_status()
        athletes = response.json()

    return [
        {"name": a.get("firstname") or a.get("name", ""), "id": a["id"]}
        for a in athletes
        if "Coaching" in (a.get("icu_tags") or [])
    ]


def _load() -> tuple[list[dict[str, str]], dict[str, str]]:
    global _cache, _cache_full
    if _cache is not None and _cache_full is not None:
        return _cache_full, _cache

    _cache_full = _fetch()
    _cache = {entry["name"].lower(): entry["id"] for entry in _cache_full}
    return _cache_full, _cache


def list_athletes() -> list[dict[str, str]]:
    """Return [{name, id}] for all coached athletes."""
    full, _ = _load()
    return full


def resolve_athlete_id(athlete_name: str) -> str:
    """Return athlete ID for the given name (case-insensitive).

    Raises ValueError with available names if not found.
    """
    full, by_name = _load()
    key = athlete_name.lower()
    if key in by_name:
        return by_name[key]

    available = ", ".join(e["name"] for e in full) if full else "no coached athletes found"
    raise ValueError(
        f"Unknown athlete '{athlete_name}'. "
        f"Available: {available}. "
        "Call icu_list_athletes to see the full list."
    )
