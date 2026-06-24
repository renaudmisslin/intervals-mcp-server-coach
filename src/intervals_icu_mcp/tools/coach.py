"""Coach-specific tools: list coached athletes from Intervals.icu."""

from __future__ import annotations

from ..athletes import list_athletes, resolve_athlete_id


async def icu_list_athletes() -> str:
    """List all athletes you coach on Intervals.icu (tagged 'Coaching').

    Call this at the start of a coaching session to discover available
    athletes. Use their first name as athlete_name in other tools, or
    pass their ID directly as athlete_id.
    """
    try:
        athletes = list_athletes()
    except Exception as e:
        return f"Error fetching coached athletes: {e}"

    if not athletes:
        return (
            "No coached athletes found. "
            "Make sure your athletes have added you as a coach on intervals.icu "
            "and that they appear with the 'Coaching' tag."
        )

    lines = [f"Coached athletes ({len(athletes)}):"]
    for a in athletes:
        lines.append(f"  - {a['name']} ({a['id']})")
    lines.append("\nUse the first name as athlete_name, or the ID as athlete_id in any tool.")
    return "\n".join(lines)


async def icu_resolve_athlete_id(athlete_name: str) -> str:
    """Resolve an athlete's first name to their Intervals.icu athlete ID.

    Use this when you have a name but need to pass athlete_id to a tool.
    Example: resolve "Luc" → "i175757".

    Args:
        athlete_name: First name of the athlete as it appears on intervals.icu.
    """
    try:
        athlete_id = resolve_athlete_id(athlete_name)
        return f"Athlete '{athlete_name}' → {athlete_id}"
    except (ValueError, Exception) as e:
        return str(e)
