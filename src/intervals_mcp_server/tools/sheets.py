"""
Google Sheets export tool for Intervals.icu MCP Server.

Exports a training session row to a Google Sheet using a Service Account.
Credentials JSON must be placed at the project root as sheets_credentials.json.
"""

import asyncio
import os
import re
from collections import defaultdict
from pathlib import Path

from intervals_mcp_server.api.client import make_intervals_request
from intervals_mcp_server.athletes import get_athlete_credentials
from intervals_mcp_server.mcp_instance import mcp

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
CREDENTIALS_FILE = Path(os.environ.get("SHEETS_CREDENTIALS", str(_PROJECT_ROOT / "sheets_credentials.json")))
SHEET_ID = os.environ.get("SHEETS_ID", "1YCfG-_nFoFac8Uz6oJbc-3-qD0_n3rrr5w_SEW2kzaQ")
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

DEFAULT_HEADERS = ["Date", "Intervalles", "Volume total", "Environnement", "Ventilation",
                   "Watts moy", "FC moy", "Efficacité", "T° moy"]


def _get_spreadsheet():
    """Return a gspread Spreadsheet, raising FileNotFoundError if credentials missing."""
    if not CREDENTIALS_FILE.exists():
        raise FileNotFoundError(
            f"Credentials Service Account introuvables : {CREDENTIALS_FILE}\n"
            "Suivez les étapes de configuration dans COACH_SETUP.md pour créer le fichier."
        )
    import gspread
    from google.oauth2.service_account import Credentials

    creds = Credentials.from_service_account_file(str(CREDENTIALS_FILE), scopes=SCOPES)
    gc = gspread.authorize(creds)
    return gc.open_by_key(SHEET_ID)


def _get_worksheet(tab_name: str):
    """Return a gspread Worksheet by tab name, raising WorksheetNotFound if absent."""
    import gspread
    sh = _get_spreadsheet()
    try:
        return sh.worksheet(tab_name)
    except gspread.exceptions.WorksheetNotFound:
        available = [ws.title for ws in sh.worksheets()]
        raise ValueError(
            f"Onglet '{tab_name}' introuvable. Onglets disponibles : {', '.join(available)}\n"
            "Utilise create_sheet_tab pour créer un nouvel onglet."
        )


def _extract_nx(title: str) -> tuple[int, int] | None:
    """Parse first NxM pattern from activity title.

    Returns (n, duration_seconds) or None if not found.
    Handles: '6x20min', '3 x 20', '6×20 PL ext', etc.
    Duration is always interpreted as minutes.
    """
    match = re.search(r"(\d+)\s*[x×]\s*(\d+)", title, re.IGNORECASE)
    if match:
        return int(match.group(1)), int(match.group(2)) * 60
    return None


def _get_candidates(icu_intervals: list[dict]) -> list[dict]:
    """Filter out rest/recovery/warmup/cooldown intervals under 60s."""
    excluded = {"rest", "active recovery", "recovery", "warmup", "cooldown", ""}
    return [
        iv for iv in icu_intervals
        if (iv.get("type") or "").lower().strip() not in excluded
        and iv.get("elapsed_time", 0) > 60
    ]


def _parse_work_intervals(
    icu_intervals: list[dict],
    activity_title: str = "",
    power_min: int = 0,
    power_max: int = 9999,
) -> list[dict]:
    """Detect main-set intervals.

    If power_min/power_max are provided, filters candidates directly by power —
    no title parsing or clustering needed.

    Otherwise:
    - Strategy 1: parse NxM from title (e.g. '6x20min')
    - Strategy 2: duration clustering, picking the highest-power bucket
    """
    candidates = _get_candidates(icu_intervals)
    if not candidates:
        return []

    # --- Explicit power filter (user confirmed via preview) ---
    if power_min > 0 or power_max < 9999:
        return [
            iv for iv in candidates
            if power_min <= (iv.get("average_watts") or iv.get("avg_watts") or 0) <= power_max
        ]

    # --- Strategy 1: NxM from title ---
    nx = _extract_nx(activity_title)
    if nx:
        n, target_sec = nx

        def _moving(iv: dict) -> int:
            return iv.get("moving_time") or iv.get("elapsed_time") or 0

        matched: list[dict] = []
        for tolerance_pct in (0.20, 0.40):
            tol = target_sec * tolerance_pct
            matched = [iv for iv in candidates if abs(_moving(iv) - target_sec) <= tol]
            if len(matched) >= n:
                break

        if matched:
            by_watts = sorted(
                matched,
                key=lambda iv: iv.get("average_watts") or iv.get("avg_watts") or 0,
                reverse=True,
            )
            selected = by_watts[:n]
            return sorted(selected, key=lambda iv: iv.get("start_index", 0))

    # --- Strategy 2: clustering by duration, pick highest-power bucket ---
    if len(candidates) == 1:
        return candidates

    def _bucket(iv: dict) -> int:
        return round(iv.get("elapsed_time", 0) / 60) * 60

    buckets: dict[int, list[dict]] = defaultdict(list)
    for iv in candidates:
        buckets[_bucket(iv)].append(iv)

    def _mean_watts(ivs: list[dict]) -> float:
        vals = [iv.get("average_watts") or iv.get("avg_watts") or 0 for iv in ivs]
        return sum(vals) / len(vals) if vals else 0

    dominant = max(buckets, key=lambda k: _mean_watts(buckets[k]))
    tolerance = max(dominant * 0.25, 60)
    return [iv for iv in candidates if abs(iv.get("elapsed_time", 0) - dominant) <= tolerance]


def _build_interval_groups(candidates: list[dict]) -> list[dict]:
    """Group candidates by duration bucket, sorted by mean power descending."""
    def _bucket(iv: dict) -> int:
        return round(iv.get("elapsed_time", 0) / 60) * 60

    buckets: dict[int, list[dict]] = defaultdict(list)
    for iv in candidates:
        buckets[_bucket(iv)].append(iv)

    groups = []
    for dur_secs, ivs in buckets.items():
        watts = [iv.get("average_watts") or iv.get("avg_watts") or 0 for iv in ivs]
        hr = [iv.get("average_heartrate") or iv.get("avg_heartrate") or 0 for iv in ivs]
        groups.append({
            "count": len(ivs),
            "duration_min": dur_secs // 60,
            "power_mean": round(sum(watts) / len(watts)) if watts else 0,
            "power_min": min(watts) if watts else 0,
            "power_max": max(watts) if watts else 0,
            "hr_mean": round(sum(hr) / len(hr)) if any(hr) else 0,
        })

    return sorted(groups, key=lambda g: -g["power_mean"])


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
    activity_id: str = "",
) -> tuple[list[str], str, str]:
    """Map activity + interval data to a sheet row aligned with headers.

    Returns (row, date_str, activity_url).
    """
    date_str = (activity.get("start_date_local") or activity.get("start_date") or "")[:10]
    activity_url = f"https://intervals.icu/activities/{activity_id}" if activity_id else ""

    is_indoor = activity.get("indoor") or activity.get("trainer") or activity.get("virtual_run")
    env = "HT" if is_indoor else "Ext"

    work_secs = sum(iv.get("moving_time") or iv.get("elapsed_time") or 0 for iv in work_intervals)
    volume = f"{round(work_secs / 60)} min" if work_secs > 0 else ""

    intervalles = _format_intervals_label(work_intervals)

    watts_vals = [iv.get("average_watts") or iv.get("avg_watts") for iv in work_intervals]
    hr_vals = [iv.get("average_heartrate") or iv.get("avg_heartrate") for iv in work_intervals]

    ef_vals: list[float | None] = []
    for iv in work_intervals:
        w = iv.get("average_watts") or iv.get("avg_watts") or 0
        h = iv.get("average_heartrate") or iv.get("avg_heartrate") or 0
        ef_vals.append(round(w / h, 2) if h else None)

    temp = activity.get("average_temp")
    if temp is None and work_intervals:
        temps = [iv.get("average_temp") for iv in work_intervals if iv.get("average_temp") is not None]
        temp = sum(temps) / len(temps) if temps else None
    if temp is not None:
        temp = round(temp)

    mapping: dict[str, str] = {
        "date": date_str,
        "intervalles": intervalles,
        "volume total": volume,
        "environnement": env,
        "ventilation": ventilation,
        "watts moy": _join([w for w in watts_vals if w is not None]),
        "fc moy": _join([h for h in hr_vals if h is not None]),
        "efficacité": _join([e for e in ef_vals if e is not None], fmt="{:.2f}"),
        "t° moy": str(temp) if temp is not None else "",
    }

    return [mapping.get(h.lower().strip(), "") for h in headers], date_str, activity_url


@mcp.tool()
async def preview_session_intervals(
    athlete_name: str,
    activity_id: str,
) -> str:
    """Preview interval groups detected in a session before exporting to Google Sheets.

    Returns a JSON string with detected groups and available sheet tabs so Claude
    can render an interactive form for the user to confirm their selection.

    JSON structure:
    {
      "athlete_name": "renaud",
      "activity_id": "i159936041",
      "activity_name": "SST x LT1",
      "groups": [
        {"label": "A", "count": 2, "duration_min": 20,
         "power_mean": 279, "power_min": 278, "power_max": 280, "hr_mean": 158}
      ],
      "available_tabs": ["renaud", "SST"]
    }

    Args:
        athlete_name: Name of the athlete as configured in athletes.json.
        activity_id: The Intervals.icu activity ID.
    """
    import json

    try:
        _athlete_id, api_key = get_athlete_credentials(athlete_name)
    except ValueError as e:
        return str(e)

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

    candidates = _get_candidates(raw_intervals)
    if not candidates:
        return json.dumps({"error": "Aucun intervalle de travail trouvé dans cette activité."})

    groups = _build_interval_groups(candidates)
    letters = "ABCDEFGHIJ"
    for i, g in enumerate(groups):
        g["label"] = letters[i] if i < len(letters) else str(i + 1)

    # Fetch available sheet tabs
    available_tabs: list[str] = []
    try:
        sh = _get_spreadsheet()
        available_tabs = [ws.title for ws in sh.worksheets()]
    except Exception:
        pass

    return json.dumps({
        "athlete_name": athlete_name,
        "activity_id": activity_id,
        "activity_name": activity.get("name", activity_id),
        "groups": groups,
        "available_tabs": available_tabs,
    }, ensure_ascii=False)


@mcp.tool()
async def export_session_to_sheet(
    athlete_name: str,
    activity_id: str,
    sheet_tab: str,
    ventilation: str = "bouche",
    power_min: int = 0,
    power_max: int = 9999,
) -> str:
    """Export a training session to a Google Sheet tab.

    Reads column headers dynamically from the Sheet, fetches activity and interval
    data from Intervals.icu, and appends a new row.

    Use preview_session_intervals first to identify the right power_min/power_max
    for the target interval group (e.g. the LT1 blocks vs SST blocks in a mixed session).

    Args:
        athlete_name: Name of the athlete as configured in athletes.json.
        activity_id: The Intervals.icu activity ID.
        sheet_tab: Target tab name (e.g. 'LT1', 'SST').
        ventilation: 'bouche' (default) or 'nez'.
        power_min: Minimum average power to include an interval (0 = no filter).
        power_max: Maximum average power to include an interval (9999 = no filter).
    """
    try:
        _athlete_id, api_key = get_athlete_credentials(athlete_name)
    except ValueError as e:
        return str(e)

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
    work_intervals = _parse_work_intervals(raw_intervals, act_title, power_min, power_max)

    try:
        ws = _get_worksheet(sheet_tab)
        headers = ws.row_values(1)
    except (FileNotFoundError, ValueError) as exc:
        return str(exc)
    except Exception as exc:
        return f"Erreur connexion Google Sheets : {exc}"

    if not headers:
        return f"La ligne 1 de l'onglet '{sheet_tab}' est vide — impossible de lire les en-têtes."

    no_intervals_warning = ""
    if not work_intervals:
        no_intervals_warning = (
            "\n⚠️  Aucun intervalle trouvé avec ces critères de puissance "
            f"({power_min}-{power_max}W).\n"
            "Utilise preview_session_intervals pour voir les groupes disponibles."
        )

    row, date_str, activity_url = _build_row(headers, activity, work_intervals, ventilation, activity_id)
    ws.append_row(row, value_input_option="USER_ENTERED")

    date_col_idx = next((i for i, h in enumerate(headers) if h.lower().strip() == "date"), None)
    if date_col_idx is not None and activity_url:
        last_row = len(ws.get_all_values())
        ws.spreadsheet.batch_update({"requests": [{"updateCells": {
            "range": {
                "sheetId": ws.id,
                "startRowIndex": last_row - 1,
                "endRowIndex": last_row,
                "startColumnIndex": date_col_idx,
                "endColumnIndex": date_col_idx + 1,
            },
            "rows": [{"values": [{"userEnteredValue": {"stringValue": date_str},
                                   "userEnteredFormat": {"textFormat": {"link": {"uri": activity_url}}}}]}],
            "fields": "userEnteredValue,userEnteredFormat.textFormat.link",
        }}]})

    act_name = activity.get("name") or activity_id
    nx_debug = f"N={nx_parsed[0]}, durée={nx_parsed[1]//60}min" if nx_parsed else "clustering / filtre puissance"
    pwr_filter = f"{power_min}-{power_max}W" if (power_min > 0 or power_max < 9999) else "aucun"
    col = {h.lower().strip(): v for h, v in zip(headers, row)}
    return (
        f"✅ Ligne ajoutée dans '{sheet_tab}' :\n"
        f"  Séance       : {act_name}\n"
        f"  Titre parsé  : {nx_debug}\n"
        f"  Filtre watts : {pwr_filter}\n"
        f"  Date         : {col.get('date', '?')}\n"
        f"  Intervalles  : {col.get('intervalles', '?')}\n"
        f"  Volume       : {col.get('volume total', '?')}\n"
        f"  Env          : {col.get('environnement', '?')} | Ventilation : {ventilation}\n"
        f"  Watts moy    : {col.get('watts moy', '?')}\n"
        f"  FC moy       : {col.get('fc moy', '?')}\n"
        f"  Efficacité   : {col.get('efficacité', '?')}\n"
        f"  T° moy       : {col.get('t° moy', '?')}"
        f"{no_intervals_warning}"
    )


@mcp.tool()
async def create_sheet_tab(
    tab_name: str,
    copy_headers_from: str = "LT1",
) -> str:
    """Create a new tab in the training Google Sheet with standard headers.

    Copies headers from an existing tab (default: 'LT1') so all tabs share
    the same structure. If the tab already exists, returns an error.

    Args:
        tab_name: Name for the new tab (e.g. 'SST', 'Threshold').
        copy_headers_from: Existing tab to copy headers from (default: 'LT1').
    """
    try:
        sh = _get_spreadsheet()
    except FileNotFoundError as exc:
        return str(exc)
    except Exception as exc:
        return f"Erreur connexion Google Sheets : {exc}"

    import gspread

    existing = [ws.title for ws in sh.worksheets()]
    if tab_name in existing:
        return f"L'onglet '{tab_name}' existe déjà. Onglets présents : {', '.join(existing)}"

    # Get headers to copy
    headers = DEFAULT_HEADERS
    if copy_headers_from and copy_headers_from in existing:
        try:
            src = sh.worksheet(copy_headers_from)
            fetched = src.row_values(1)
            if fetched:
                headers = fetched
        except Exception:
            pass

    new_ws = sh.add_worksheet(title=tab_name, rows=1000, cols=len(headers))
    new_ws.append_row(headers)

    # Bold the header row
    new_ws.spreadsheet.batch_update({"requests": [{"repeatCell": {
        "range": {
            "sheetId": new_ws.id,
            "startRowIndex": 0,
            "endRowIndex": 1,
        },
        "cell": {"userEnteredFormat": {"textFormat": {"bold": True}}},
        "fields": "userEnteredFormat.textFormat.bold",
    }}]})

    return (
        f"✅ Onglet '{tab_name}' créé avec {len(headers)} colonnes :\n"
        f"  {' | '.join(headers)}\n"
        f"  (headers copiés depuis '{copy_headers_from}')"
    )
