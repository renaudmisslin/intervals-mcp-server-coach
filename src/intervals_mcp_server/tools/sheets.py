"""
Google Sheets export tool for Intervals.icu MCP Server.

Exports a training session row to a Google Sheet using a Service Account.
Credentials JSON must be placed at the project root as sheets_credentials.json.
"""

import asyncio
import os
import re
from pathlib import Path
from typing import Any

from intervals_mcp_server.api.client import make_intervals_request
from intervals_mcp_server.athletes import get_athlete_credentials
from intervals_mcp_server.mcp_instance import mcp

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
CREDENTIALS_FILE = Path(os.environ.get("SHEETS_CREDENTIALS", str(_PROJECT_ROOT / "sheets_credentials.json")))
SHEET_ID = os.environ.get("SHEETS_ID", "17bx2t7ynvSRK4c5XoWaMhea7ovALw1-2qzESbfYTnvs")
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def _get_worksheet(tab_name: str = "Feuille 1"):
    """Return a gspread Worksheet, raising FileNotFoundError if credentials missing."""
    if not CREDENTIALS_FILE.exists():
        raise FileNotFoundError(
            f"Credentials Service Account introuvables : {CREDENTIALS_FILE}\n"
            "Suivez les étapes de configuration dans COACH_SETUP.md pour créer le fichier."
        )
    import gspread
    from google.oauth2.service_account import Credentials

    creds = Credentials.from_service_account_file(str(CREDENTIALS_FILE), scopes=SCOPES)
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(SHEET_ID)
    try:
        return sh.worksheet(tab_name)
    except gspread.exceptions.WorksheetNotFound:
        return sh.sheet1


def _extract_nx(title: str) -> tuple[int, int] | None:
    """Parse first NxM pattern from activity title, ignoring any suffix.

    Returns (n, duration_seconds) or None if not found.
    Handles: '6x20min', '3 x 20' PL', 'LT1 6x20min ext', '6×20 PL ext', etc.
    Duration is always interpreted as minutes.
    """
    match = re.search(r"(\d+)\s*[x×]\s*(\d+)", title, re.IGNORECASE)
    if match:
        return int(match.group(1)), int(match.group(2)) * 60
    return None


def _parse_work_intervals(icu_intervals: list[dict], activity_title: str = "") -> list[dict]:
    """Detect main-set intervals using the activity title when possible.

    Strategy 1 (title): if title contains 'NxM' (e.g. '6x20min'), filter intervals
    whose moving_time ≈ M ± 20%, then take the N most intense (highest avg watts).
    Widens to ±40% if fewer than N are found at ±20%.

    Strategy 2 (fallback): duration clustering — returns the dominant repeated block.
    """
    from collections import Counter

    excluded = {"rest", "active recovery", "recovery", "warmup", "cooldown", ""}
    candidates = [
        iv for iv in icu_intervals
        if (iv.get("type") or "").lower().strip() not in excluded
        and iv.get("elapsed_time", 0) > 60
    ]

    if not candidates:
        return []

    # --- Strategy 1: use NxM from title ---
    nx = _extract_nx(activity_title)
    if nx:
        n, target_sec = nx

        def _moving(iv: dict) -> int:
            return iv.get("moving_time") or iv.get("elapsed_time") or 0

        for tolerance_pct in (0.20, 0.40):
            tol = target_sec * tolerance_pct
            matched = [iv for iv in candidates if abs(_moving(iv) - target_sec) <= tol]
            if len(matched) >= n:
                break

        if matched:
            # Select the N most intense, then restore chronological order
            by_watts = sorted(
                matched,
                key=lambda iv: iv.get("average_watts") or iv.get("avg_watts") or 0,
                reverse=True,
            )
            selected = by_watts[:n]
            return sorted(selected, key=lambda iv: iv.get("start_index", 0))

    # --- Strategy 2: duration clustering fallback ---
    if len(candidates) == 1:
        return candidates

    def _bucket(iv: dict) -> int:
        return round(iv.get("elapsed_time", 0) / 60) * 60

    counts = Counter(_bucket(iv) for iv in candidates)
    dominant = counts.most_common(1)[0][0]
    tolerance = max(dominant * 0.25, 60)
    return [iv for iv in candidates if abs(iv.get("elapsed_time", 0) - dominant) <= tolerance]


def _format_intervals_label(work_intervals: list[dict]) -> str:
    """Format as '3 x 20'' from work intervals."""
    if not work_intervals:
        return ""
    n = len(work_intervals)
    avg_min = round(sum(iv.get("elapsed_time", 0) for iv in work_intervals) / n / 60)
    return f"{n} x {avg_min}'"


def _join(values: list, fmt: str = "{:.0f}") -> str:
    """Join a list of numbers as '270-271-269', skipping None."""
    return "-".join(fmt.format(v) for v in values if v is not None)


def _build_row(
    headers: list[str],
    activity: dict,
    work_intervals: list[dict],
    ventilation: str,
) -> list[str]:
    """Map activity + interval data to a row aligned with Sheet headers."""
    # Date
    date = (activity.get("start_date_local") or activity.get("start_date") or "")[:10]

    # Environnement: indoor/trainer → HT, else Ext
    is_indoor = activity.get("indoor") or activity.get("trainer") or activity.get("virtual_run")
    env = "HT" if is_indoor else "Ext"

    # Volume total = somme du moving_time des intervalles de travail (N × durée bloc)
    work_secs = sum(iv.get("moving_time") or iv.get("elapsed_time") or 0 for iv in work_intervals)
    if work_secs > 0:
        wh, wm = divmod(round(work_secs / 60), 60)
        volume = f"{wh}h{wm:02d}" if wh else f"{wm} min"
    else:
        volume = ""

    # Intervals label
    intervalles = _format_intervals_label(work_intervals)

    # Per-interval metrics
    watts_vals = [iv.get("average_watts") or iv.get("avg_watts") for iv in work_intervals]
    hr_vals = [iv.get("average_heartrate") or iv.get("avg_heartrate") for iv in work_intervals]

    # Efficacité = EF per interval (avg_watts / avg_hr, rounded to 2 dec)
    ef_vals: list[float | None] = []
    for iv in work_intervals:
        w = iv.get("average_watts") or iv.get("avg_watts") or 0
        h = iv.get("average_heartrate") or iv.get("avg_heartrate") or 0
        ef_vals.append(round(w / h, 2) if h else None)

    # Temperature: from activity, or average across work intervals
    temp = activity.get("average_temp")
    if temp is None and work_intervals:
        temps = [iv.get("average_temp") for iv in work_intervals if iv.get("average_temp") is not None]
        temp = sum(temps) / len(temps) if temps else None
    if temp is not None:
        temp = round(temp)

    mapping: dict[str, str] = {
        "date": date,
        "intervalles": intervalles,
        "volume total": volume,
        "environnement": env,
        "ventilation": ventilation,
        "watts moy": _join([w for w in watts_vals if w is not None]),
        "fc moy": _join([h for h in hr_vals if h is not None]),
        "efficacité": _join([e for e in ef_vals if e is not None], fmt="{:.2f}"),
        "t° moy": str(temp) if temp is not None else "",
    }

    return [mapping.get(h.lower().strip(), "") for h in headers]


@mcp.tool()
async def export_session_to_sheet(
    athlete_name: str,
    activity_id: str,
    ventilation: str = "bouche",
    sheet_tab: str = "Feuille 1",
) -> str:
    """Export a training session to the Google Sheet 'suivi LT1'.

    Reads column headers dynamically from the Sheet, fetches activity and interval
    data from Intervals.icu, maps the fields, and appends a new row.

    Columns populated:
    - Date: session date
    - Intervalles: structure e.g. '3 x 20''
    - Volume total: distance (km) or duration (min) if indoor
    - Environnement: HT (indoor/trainer) or Ext (outdoor)
    - Ventilation: provided parameter (default 'bouche')
    - Watts moy: average power per work interval, e.g. '270-271-269'
    - FC moy: average heart rate per work interval, e.g. '145-146-142'
    - Efficacité: EF (watts/HR) per work interval, e.g. '1.86-1.87-1.88'
    - T° moy: average temperature

    Requires sheets_credentials.json (Service Account) at the project root.
    See COACH_SETUP.md for setup instructions.

    Args:
        athlete_name: Name of the athlete as configured in athletes.json.
        activity_id: The Intervals.icu activity ID.
        ventilation: "bouche" (default) or "nez".
        sheet_tab: Tab name in the Sheet (default: "Feuille 1").
    """
    try:
        _athlete_id, api_key = get_athlete_credentials(athlete_name)
    except ValueError as e:
        return str(e)

    # Fetch activity details and intervals concurrently
    activity_result, intervals_result = await asyncio.gather(
        make_intervals_request(url=f"/activity/{activity_id}", api_key=api_key),
        make_intervals_request(url=f"/activity/{activity_id}/intervals", api_key=api_key),
    )

    if isinstance(activity_result, dict) and "error" in activity_result:
        return f"Erreur activité : {activity_result.get('message')}"
    if isinstance(intervals_result, dict) and "error" in intervals_result:
        return f"Erreur intervalles : {intervals_result.get('message')}"

    activity: dict = activity_result[0] if isinstance(activity_result, list) else activity_result
    raw_intervals: list[dict] = (
        intervals_result.get("icu_intervals", []) if isinstance(intervals_result, dict) else []
    )
    act_title = activity.get("name", "")
    nx_parsed = _extract_nx(act_title)
    work_intervals = _parse_work_intervals(raw_intervals, act_title)

    # Open Sheet and read headers from row 1
    try:
        ws = _get_worksheet(sheet_tab)
        headers = ws.row_values(1)
    except FileNotFoundError as exc:
        return str(exc)
    except Exception as exc:
        return f"Erreur connexion Google Sheets : {exc}"

    if not headers:
        return "La ligne 1 du Sheet est vide — impossible de lire les en-têtes."

    no_intervals_warning = ""
    if not work_intervals:
        no_intervals_warning = (
            "\n⚠️  Aucun intervalle de travail détecté — colonnes Intervalles, Volume, "
            "Watts moy, FC moy et Efficacité laissées vides.\n"
            "Cause probable : les intervalles ne sont pas définis sur cette activité dans Intervals.icu.\n"
            "Solutions :\n"
            "  1. Sur intervals.icu, ouvre l'activité → vérifie qu'il y a des intervalles visibles\n"
            "  2. Si non : crée-les manuellement (icône ciseaux) ou relance l'analyse automatique\n"
            "  3. Une fois les intervalles présents, relance l'export\n"
            "Vérification secondaire : le titre doit contenir un pattern NxM (ex: '3x20min')"
        )

    row = _build_row(headers, activity, work_intervals, ventilation)
    ws.append_row(row, value_input_option="USER_ENTERED")

    act_name = activity.get("name") or activity_id
    nx_debug = f"N={nx_parsed[0]}, durée={nx_parsed[1]//60}min" if nx_parsed else "non détecté (fallback clustering)"
    col = {h.lower().strip(): v for h, v in zip(headers, row)}
    return (
        f"✅ Ligne ajoutée dans '{sheet_tab}' :\n"
        f"  Séance     : {act_name}\n"
        f"  Titre parsé: {nx_debug}\n"
        f"  Date       : {col.get('date', '?')}\n"
        f"  Intervalles: {col.get('intervalles', '?')}\n"
        f"  Volume     : {col.get('volume total', '?')}\n"
        f"  Env        : {col.get('environnement', '?')} | Ventilation : {ventilation}\n"
        f"  Watts moy  : {col.get('watts moy', '?')}\n"
        f"  FC moy     : {col.get('fc moy', '?')}\n"
        f"  Efficacité : {col.get('efficacité', '?')}\n"
        f"  T° moy     : {col.get('t° moy', '?')}"
        f"{no_intervals_warning}"
    )
