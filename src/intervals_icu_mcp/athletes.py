"""Multi-athlete name→ID resolution loaded from athletes.json."""

from __future__ import annotations

import json
from pathlib import Path

_cache: dict[str, str] | None = None


def _load() -> dict[str, str]:
    global _cache
    if _cache is not None:
        return _cache

    candidates = [
        Path(__file__).parent.parent.parent.parent / "athletes.json",
        Path(__file__).parent.parent.parent / "athletes.json",
        Path("athletes.json"),
    ]
    for path in candidates:
        if path.exists():
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            _cache = data.get("athletes", {})
            return _cache

    raise FileNotFoundError(
        "athletes.json not found. "
        "Create it from athletes.json.example at the project root."
    )


def list_athlete_names() -> list[str]:
    """Return all configured athlete names."""
    return list(_load().keys())


def resolve_athlete_id(athlete_name: str) -> str:
    """Return the Intervals.icu athlete ID for the given name.

    Raises ValueError with available names if the name is unknown.
    """
    athletes = _load()
    if athlete_name not in athletes:
        available = ", ".join(athletes.keys()) if athletes else "no athletes configured"
        raise ValueError(
            f"Unknown athlete '{athlete_name}'. "
            f"Available: {available}. "
            "Call icu_list_athletes to see the full list."
        )
    return athletes[athlete_name]
