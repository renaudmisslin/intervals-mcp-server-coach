"""Coach-specific tools: list_athletes, post_activity_comment, get_training_load."""

from __future__ import annotations

import json
from datetime import date, timedelta
from typing import Any

from intervals_mcp_server.api.client import make_intervals_request
from intervals_mcp_server.athletes import get_athlete_credentials, list_athlete_names
from intervals_mcp_server.mcp_instance import mcp


@mcp.tool()
async def list_athletes() -> str:
    """List all athletes configured in athletes.json.

    Call this tool at the start of every conversation to know which athlete names
    are available before calling any other tool.
    """
    names = list_athlete_names()
    if not names:
        return (
            "Aucun athlète configuré. "
            "Remplissez athletes.json à la racine du projet (voir athletes.json.example)."
        )
    return (
        f"Athlètes disponibles ({len(names)}) : {', '.join(names)}.\n"
        "Utilisez l'un de ces noms comme paramètre athlete_name dans toutes les autres requêtes."
    )


@mcp.tool()
async def post_activity_comment(
    athlete_name: str,
    activity_id: str,
    content: str,
) -> str:
    """Post a comment on an athlete's activity.

    Args:
        athlete_name: Name of the athlete as configured in athletes.json.
        activity_id: The Intervals.icu activity ID (e.g. "12345678").
        content: The comment text to post.
    """
    try:
        athlete_id, api_key = get_athlete_credentials(athlete_name)
    except ValueError as e:
        return str(e)

    if not content.strip():
        return "Erreur : le contenu du commentaire ne peut pas être vide."

    result = await make_intervals_request(
        url=f"/activity/{activity_id}/messages",
        api_key=api_key,
        method="POST",
        data={"content": content},
    )

    if isinstance(result, dict) and result.get("error"):
        return f"Erreur lors de l'envoi du commentaire : {result.get('message', result)}"

    return f"Commentaire publié avec succès sur l'activité {activity_id} pour {athlete_name}."


@mcp.tool()
async def get_training_load(
    athlete_name: str,
    start_date: str | None = None,
    end_date: str | None = None,
) -> str:
    """Get CTL (Fitness), ATL (Fatigue), and TSB (Form) for an athlete over a period.

    Args:
        athlete_name: Name of the athlete as configured in athletes.json.
        start_date: Start date in YYYY-MM-DD format (default: 42 days ago).
        end_date: End date in YYYY-MM-DD format (default: today).
    """
    try:
        athlete_id, api_key = get_athlete_credentials(athlete_name)
    except ValueError as e:
        return str(e)

    today = date.today()
    oldest = start_date or (today - timedelta(days=42)).isoformat()
    newest = end_date or today.isoformat()

    result = await make_intervals_request(
        url=f"/athlete/{athlete_id}/fitnesses",
        api_key=api_key,
        params={"oldest": oldest, "newest": newest},
    )

    if isinstance(result, dict) and result.get("error"):
        return f"Erreur API : {result.get('message', result)}"

    if not isinstance(result, list) or len(result) == 0:
        return f"Aucune donnée de charge d'entraînement disponible pour {athlete_name} sur la période {oldest} → {newest}."

    rows: list[str] = [f"Charge d'entraînement de {athlete_name} ({oldest} → {newest})\n"]
    rows.append(f"{'Date':<12} {'CTL (Forme)':>12} {'ATL (Fatigue)':>14} {'TSB (Fraîcheur)':>16}")
    rows.append("-" * 56)

    for entry in result:
        d = entry.get("date", "")[:10]
        ctl = entry.get("ctl")
        atl = entry.get("atl")
        form = entry.get("form")

        ctl_str = f"{ctl:.1f}" if ctl is not None else "—"
        atl_str = f"{atl:.1f}" if atl is not None else "—"
        form_str = f"{form:+.1f}" if form is not None else "—"
        rows.append(f"{d:<12} {ctl_str:>12} {atl_str:>14} {form_str:>16}")

    latest = result[-1]
    ctl = latest.get("ctl")
    atl = latest.get("atl")
    form = latest.get("form")

    rows.append("")
    if form is not None:
        if form > 5:
            status = "Athlète frais — bon pour une compétition ou une séance intense."
        elif form > -10:
            status = "Athlète en bonne forme — entraînement productif possible."
        elif form > -30:
            status = "Athlète fatigué — prévoir récupération."
        else:
            status = "Athlète très fatigué — repos recommandé."
        rows.append(f"Interprétation (au {latest.get('date', '')[:10]}) : {status}")

    return "\n".join(rows)
