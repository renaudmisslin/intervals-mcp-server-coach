"""Multi-athlete credentials management loaded from athletes.json."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_cache: dict[str, Any] | None = None


def _load() -> dict[str, Any]:
    global _cache
    if _cache is not None:
        return _cache

    candidates = [
        Path(__file__).parent.parent.parent.parent / "athletes.json",  # repo root from src/pkg/
        Path(__file__).parent.parent.parent / "athletes.json",
        Path("athletes.json"),
    ]
    for path in candidates:
        if path.exists():
            with open(path, encoding="utf-8") as f:
                _cache = json.load(f)
            return _cache

    raise FileNotFoundError(
        "Fichier athletes.json introuvable. "
        "Créez-le à la racine du projet en vous basant sur athletes.json.example"
    )


def list_athlete_names() -> list[str]:
    """Return all configured athlete names."""
    return list(_load().get("athletes", {}).keys())


def get_athlete_credentials(athlete_name: str) -> tuple[str, str]:
    """Return (athlete_id, api_key) for the given athlete name.

    Raises ValueError with a helpful message if the name is unknown.
    """
    athletes = _load().get("athletes", {})
    if athlete_name not in athletes:
        available = ", ".join(athletes.keys()) if athletes else "aucun athlète configuré"
        raise ValueError(
            f"Athlète '{athlete_name}' inconnu. "
            f"Athlètes disponibles : {available}"
        )
    entry = athletes[athlete_name]
    return entry["id"], entry["api_key"]
