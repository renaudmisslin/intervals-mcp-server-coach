"""
Wellness-related MCP tools for Intervals.icu.

This module contains tools for retrieving athlete wellness data.
"""

from intervals_mcp_server.api.client import make_intervals_request
from intervals_mcp_server.utils.formatting import format_query_meta, format_wellness_entry
from intervals_mcp_server.utils.validation import resolve_date_params

# Import mcp instance from shared module for tool registration
from intervals_mcp_server.mcp_instance import mcp  # noqa: F401
from intervals_mcp_server.athletes import get_athlete_credentials


@mcp.tool()
async def get_wellness_data(
    athlete_name: str,
    start_date: str | None = None,
    end_date: str | None = None,
    include_all_fields: bool = False,
) -> str:
    """Get wellness data for an athlete from Intervals.icu.

    By default returns standard wellness fields (training metrics, vitals, sleep,
    subjective scores, etc.). Set include_all_fields=True to also include any
    additional or custom fields configured by the user in Intervals.icu.

    Args:
        athlete_id: The Intervals.icu athlete ID (optional, will use ATHLETE_ID from .env if not provided)
        api_key: The Intervals.icu API key (optional, will use API_KEY from .env if not provided)
        start_date: Start date in YYYY-MM-DD format (optional, defaults to 30 days ago)
        end_date: End date in YYYY-MM-DD format (optional, defaults to today)
        include_all_fields: If True, include additional and custom fields beyond the standard set (optional, defaults to False)
    """
    try:
        athlete_id, api_key = get_athlete_credentials(athlete_name)
    except ValueError as e:
        return str(e)

    start_date, end_date = resolve_date_params(start_date, end_date)

    params = {"oldest": start_date, "newest": end_date}

    result = await make_intervals_request(
        url=f"/athlete/{athlete_id}/wellness", api_key=api_key, params=params
    )

    if isinstance(result, dict) and "error" in result:
        return f"Error fetching wellness data: {result.get('message')}"

    if not result:
        return (
            f"No wellness data found for athlete {athlete_id} in the specified date range."
        )

    wellness_summary = "Wellness Data:\n\n"
    count = 0

    if isinstance(result, dict):
        for date_str, data in result.items():
            if isinstance(data, dict) and "date" not in data:
                data["date"] = date_str
            wellness_summary += format_wellness_entry(data, include_all_fields=include_all_fields) + "\n\n"
            count += 1
    elif isinstance(result, list):
        for entry in result:
            if isinstance(entry, dict):
                wellness_summary += format_wellness_entry(entry, include_all_fields=include_all_fields) + "\n\n"
                count += 1

    wellness_summary += format_query_meta(count, count, start_date, end_date)
    return wellness_summary


@mcp.tool()
async def update_wellness_nutrition(
    athlete_name: str,
    date: str,
    carbohydrates_g: float | None = None,
    protein_g: float | None = None,
    fat_g: float | None = None,
    kcal: float | None = None,
    hydration_ml: float | None = None,
) -> str:
    """Write nutrition data to Intervals.icu wellness for a specific date.

    Updates macronutrients and/or hydration for one day. Only provided fields
    are sent — existing fields on that day are preserved.

    Args:
        athlete_name: Name of the athlete as configured in athletes.json.
        date: Date in YYYY-MM-DD format (e.g. '2026-06-20').
        carbohydrates_g: Carbohydrates in grams.
        protein_g: Protein in grams.
        fat_g: Total fat in grams.
        kcal: Total calories (kcal). If omitted and macros provided, not auto-calculated.
        hydration_ml: Hydration volume in millilitres.
    """
    try:
        athlete_id, api_key = get_athlete_credentials(athlete_name)
    except ValueError as e:
        return str(e)

    payload: dict = {}
    if carbohydrates_g is not None:
        payload["carbohydrates"] = carbohydrates_g
    if protein_g is not None:
        payload["protein"] = protein_g
    if fat_g is not None:
        payload["fatTotal"] = fat_g
    if kcal is not None:
        payload["kcalConsumed"] = kcal
    if hydration_ml is not None:
        payload["hydrationVolume"] = hydration_ml

    if not payload:
        return "Aucune valeur fournie — rien à enregistrer."

    result = await make_intervals_request(
        url=f"/athlete/{athlete_id}/wellness/{date}",
        api_key=api_key,
        method="PUT",
        data=payload,
    )

    if isinstance(result, dict) and "error" in result:
        return f"Erreur lors de l'enregistrement : {result.get('message', 'inconnue')}"

    lines = [f"✅ Nutrition enregistrée pour {athlete_name} le {date} :"]
    if carbohydrates_g is not None:
        lines.append(f"  Glucides : {carbohydrates_g} g")
    if protein_g is not None:
        lines.append(f"  Protéines : {protein_g} g")
    if fat_g is not None:
        lines.append(f"  Lipides : {fat_g} g")
    if kcal is not None:
        lines.append(f"  Calories : {kcal} kcal")
    if hydration_ml is not None:
        lines.append(f"  Hydratation : {hydration_ml} ml")
    return "\n".join(lines)
