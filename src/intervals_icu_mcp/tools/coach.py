"""Coach-specific tools: list configured athletes."""

from __future__ import annotations

from ..athletes import list_athlete_names


async def icu_list_athletes() -> str:
    """List all athletes configured in athletes.json.

    Call this at the start of a coaching session to discover which athlete
    names are available. Use those names as the athlete_name parameter in
    other tools, or pass the corresponding athlete ID directly as athlete_id.
    """
    try:
        names = list_athlete_names()
    except FileNotFoundError as e:
        return str(e)

    if not names:
        return (
            "No athletes configured. "
            "Edit athletes.json at the project root (see athletes.json.example)."
        )

    return (
        f"Configured athletes ({len(names)}): {', '.join(names)}.\n"
        "Use these names to look up athlete IDs, or pass them directly as athlete_name "
        "when tools support it. For tools that only accept athlete_id, call "
        "icu_resolve_athlete_id to get the ID for a given name."
    )


async def icu_resolve_athlete_id(athlete_name: str) -> str:
    """Resolve an athlete name (from athletes.json) to their Intervals.icu athlete ID.

    Use this when you have an athlete name but need to pass an athlete_id
    to a tool. For example: resolve "thomas" → "i67890", then pass
    athlete_id="i67890" to icu_get_wellness_data.

    Args:
        athlete_name: Name of the athlete as configured in athletes.json.
    """
    from ..athletes import resolve_athlete_id

    try:
        athlete_id = resolve_athlete_id(athlete_name)
        return f"Athlete '{athlete_name}' → {athlete_id}"
    except (ValueError, FileNotFoundError) as e:
        return str(e)
