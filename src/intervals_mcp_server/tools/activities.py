"""
Activity-related MCP tools for Intervals.icu.

This module contains tools for retrieving and managing athlete activities.
"""

from datetime import datetime, timedelta
from typing import Any

from intervals_mcp_server.api.client import make_intervals_request
from intervals_mcp_server.tools.gear import (
    resolve_gear_for_activity,
    resolve_gear_for_activities,
)
from intervals_mcp_server.utils.formatting import (
    format_activity_brief,
    format_activity_message,
    format_activity_summary,
    format_intervals,
    format_query_meta,
)
from intervals_mcp_server.utils.validation import resolve_date_params

# Import mcp instance from shared module for tool registration
from intervals_mcp_server.mcp_instance import mcp  # noqa: F401
from intervals_mcp_server.athletes import get_athlete_credentials


def _parse_activities_from_result(result: Any) -> list[dict[str, Any]]:
    """Extract a list of activity dictionaries from the API result."""
    activities: list[dict[str, Any]] = []

    if isinstance(result, list):
        activities = [item for item in result if isinstance(item, dict)]
    elif isinstance(result, dict):
        # Result is a single activity or a container
        for _key, value in result.items():
            if isinstance(value, list):
                activities = [item for item in value if isinstance(item, dict)]
                break
        # If no list was found but the dict has typical activity fields, treat it as a single activity
        if not activities and any(key in result for key in ["name", "startTime", "distance"]):
            activities = [result]

    return activities


def _filter_named_activities(activities: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Filter out unnamed activities from the list."""
    return [
        activity
        for activity in activities
        if activity.get("name") and activity.get("name") != "Unnamed"
    ]


async def _fetch_more_activities(
    athlete_id: str,
    start_date: str,
    api_key: str | None,
    api_limit: int,
) -> list[dict[str, Any]]:
    """Fetch additional activities from an earlier date range."""
    oldest_date = datetime.fromisoformat(start_date)
    older_start_date = (oldest_date - timedelta(days=60)).strftime("%Y-%m-%d")
    older_end_date = (oldest_date - timedelta(days=1)).strftime("%Y-%m-%d")

    if older_start_date >= older_end_date:
        return []

    more_params = {
        "oldest": older_start_date,
        "newest": older_end_date,
        "limit": api_limit,
    }
    more_result = await make_intervals_request(
        url=f"/athlete/{athlete_id}/activities",
        api_key=api_key,
        params=more_params,
    )

    if isinstance(more_result, list):
        return _filter_named_activities(more_result)
    return []


def _apply_activity_filters(
    activities: list[dict[str, Any]],
    activity_type: str | None,
    min_distance_km: float | None,
    min_duration_min: float | None,
    min_elevation_m: float | None,
    min_training_load: float | None,
) -> list[dict[str, Any]]:
    """Apply optional filters to an activity list. No extra API calls."""
    result = activities
    if activity_type:
        at_lower = activity_type.lower()
        result = [
            a for a in result
            if at_lower in (a.get("type") or "").lower()
            or at_lower in (a.get("sport_type") or "").lower()
        ]
    if min_distance_km is not None:
        min_m = min_distance_km * 1000
        result = [a for a in result if (a.get("distance") or 0) >= min_m]
    if min_duration_min is not None:
        min_s = min_duration_min * 60
        result = [
            a for a in result
            if (a.get("moving_time") or a.get("elapsed_time") or 0) >= min_s
        ]
    if min_elevation_m is not None:
        result = [a for a in result if (a.get("total_elevation_gain") or 0) >= min_elevation_m]
    if min_training_load is not None:
        result = [
            a for a in result
            if (a.get("icu_training_load") or a.get("training_load") or 0) >= min_training_load
        ]
    return result


@mcp.tool()
async def get_activities(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    athlete_name: str,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 10,
    include_unnamed: bool = False,
    detail_level: str = "brief",
    activity_type: str | None = None,
    min_distance_km: float | None = None,
    min_duration_min: float | None = None,
    min_elevation_m: float | None = None,
    min_training_load: float | None = None,
) -> str:
    """Get a list of activities for an athlete from Intervals.icu.

    By default returns a compact one-line summary per activity (detail_level='brief').
    Request detail_level='full' only when the user explicitly asks for complete metrics.

    Filters are applied server-side to the fetched list — no extra API calls.
    Use filters to narrow results before displaying (e.g. only rides over 100km).

    Args:
        athlete_name: Name of the athlete as configured in athletes.json.
        start_date: Start date YYYY-MM-DD (default: 30 days ago).
        end_date: End date YYYY-MM-DD (default: today).
        limit: Max activities to return after filtering (default: 10).
        include_unnamed: Include activities without a name (default: False).
        detail_level: 'brief' (default) = compact one-liner per activity.
                      'full' = all metrics (only when explicitly requested).
        activity_type: Filter by sport type, e.g. 'Ride', 'Run', 'Swim' (case-insensitive).
        min_distance_km: Only return activities >= this distance in km.
        min_duration_min: Only return activities >= this duration in minutes.
        min_elevation_m: Only return activities >= this elevation gain in meters.
        min_training_load: Only return activities >= this training load score.
    """
    try:
        athlete_id, api_key = get_athlete_credentials(athlete_name)
    except ValueError as e:
        return str(e)

    start_date, end_date = resolve_date_params(start_date, end_date)

    # Fetch extra to absorb unnamed + filter losses
    has_filters = any(v is not None for v in [activity_type, min_distance_km, min_duration_min, min_elevation_m, min_training_load])
    api_limit = limit * (5 if has_filters else 3) if not include_unnamed else limit * (3 if has_filters else 1)

    params = {"oldest": start_date, "newest": end_date, "limit": api_limit}
    result = await make_intervals_request(
        url=f"/athlete/{athlete_id}/activities", api_key=api_key, params=params
    )

    if isinstance(result, dict) and "error" in result:
        return f"Error fetching activities: {result.get('message', 'Unknown error')}"
    if not result:
        return f"No activities found for athlete {athlete_id} in the specified date range."

    activities = _parse_activities_from_result(result)
    if not activities:
        return f"No valid activities found for athlete {athlete_id} in the specified date range."

    if not include_unnamed:
        activities = _filter_named_activities(activities)
        if len(activities) < limit:
            more = await _fetch_more_activities(athlete_id, start_date, api_key, api_limit)
            activities.extend(more)

    count_scanned = len(activities)

    # Apply optional filters (no extra API calls — data already fetched)
    if has_filters:
        activities = _apply_activity_filters(
            activities, activity_type, min_distance_km, min_duration_min,
            min_elevation_m, min_training_load,
        )

    activities = activities[:limit]
    count_returned = len(activities)

    if not activities:
        filter_desc = []
        if activity_type: filter_desc.append(f"type={activity_type}")
        if min_distance_km: filter_desc.append(f">={min_distance_km}km")
        if min_duration_min: filter_desc.append(f">={min_duration_min}min")
        if min_elevation_m: filter_desc.append(f">={min_elevation_m}m↑")
        if min_training_load: filter_desc.append(f"TL>={min_training_load}")
        filters_str = ", ".join(filter_desc)
        base = f"No activities found for {athlete_name} matching filters ({filters_str})." if filters_str else f"No activities found for {athlete_name}."
        return base + format_query_meta(count_scanned, 0, start_date, end_date)

    if detail_level == "full":
        await resolve_gear_for_activities(activities, athlete_id=athlete_id, api_key=api_key)
        output = "Activities:\n\n"
        for activity in activities:
            output += format_activity_summary(activity) + "\n"
    else:
        output = "Activities:\n\n"
        for activity in activities:
            output += format_activity_brief(activity) + "\n"
        output += "\n💡 Pour les détails complets d'une séance : get_activity_details(athlete_name, activity_id)"

    output += format_query_meta(count_scanned, count_returned, start_date, end_date)
    return output


@mcp.tool()
async def get_activity_details(
    athlete_name: str,
    activity_id: str,
) -> str:
    """Get detailed information for a specific activity from Intervals.icu

    Args:
        athlete_name: Name of the athlete as configured in athletes.json.
        activity_id: The Intervals.icu activity ID.
    """
    try:
        athlete_id, api_key = get_athlete_credentials(athlete_name)
    except ValueError as e:
        return str(e)
    result = await make_intervals_request(url=f"/activity/{activity_id}", api_key=api_key)

    if isinstance(result, dict) and "error" in result:
        error_message = result.get("message", "Unknown error")
        return f"Error fetching activity details: {error_message}"

    # Format the response
    if not result:
        return f"No details found for activity {activity_id}."

    # If result is a list, use the first item if available
    activity_data = result[0] if isinstance(result, list) and result else result
    if not isinstance(activity_data, dict):
        return f"Invalid activity format for activity {activity_id}."

    await resolve_gear_for_activity(activity_data, athlete_id=athlete_id, api_key=api_key)

    # Return a more detailed view of the activity
    detailed_view = format_activity_summary(activity_data)

    # Add additional details if available
    if "zones" in activity_data:
        zones = activity_data["zones"]
        detailed_view += "\nPower Zones:\n"
        for zone in zones.get("power", []):
            detailed_view += f"Zone {zone.get('number')}: {zone.get('secondsInZone')} seconds\n"

        detailed_view += "\nHeart Rate Zones:\n"
        for zone in zones.get("hr", []):
            detailed_view += f"Zone {zone.get('number')}: {zone.get('secondsInZone')} seconds\n"

    return detailed_view


@mcp.tool()
async def get_activity_intervals(
    athlete_name: str,
    activity_id: str,
) -> str:
    """Get interval data for a specific activity from Intervals.icu

    Args:
        athlete_name: Name of the athlete as configured in athletes.json.
        activity_id: The Intervals.icu activity ID.
    """
    try:
        _athlete_id, api_key = get_athlete_credentials(athlete_name)
    except ValueError as e:
        return str(e)
    result = await make_intervals_request(url=f"/activity/{activity_id}/intervals", api_key=api_key)

    if isinstance(result, dict) and "error" in result:
        error_message = result.get("message", "Unknown error")
        return f"Error fetching intervals: {error_message}"

    # Format the response
    if not result:
        return f"No interval data found for activity {activity_id}."

    # If the result is empty or doesn't contain expected fields
    if not isinstance(result, dict) or not any(
        key in result for key in ["icu_intervals", "icu_groups"]
    ):
        return f"No interval data or unrecognized format for activity {activity_id}."

    # Format the intervals data
    return format_intervals(result)


@mcp.tool()
async def get_activity_streams(
    athlete_name: str,
    activity_id: str,
    stream_types: str | None = None,
) -> str:
    """Get stream data for a specific activity from Intervals.icu

    This endpoint returns time-series data for an activity, including metrics like power, heart rate,
    cadence, altitude, distance, temperature, and velocity data.

    Args:
        activity_id: The Intervals.icu activity ID
        api_key: The Intervals.icu API key (optional, will use API_KEY from .env if not provided)
        stream_types: Comma-separated list of stream types to retrieve (optional, defaults to all available types)
                     Available types: time, watts, heartrate, cadence, altitude, distance,
                     core_temperature, skin_temperature, velocity_smooth
    """
    try:
        _athlete_id, api_key = get_athlete_credentials(athlete_name)
    except ValueError as e:
        return str(e)
    params = {}
    if stream_types:
        params["types"] = stream_types
    else:
        params["types"] = "time,watts,heartrate,cadence,altitude,distance,velocity_smooth"

    result = await make_intervals_request(
        url=f"/activity/{activity_id}/streams",
        api_key=api_key,
        params=params,
    )

    if isinstance(result, dict) and "error" in result:
        error_message = result.get("message", "Unknown error")
        return f"Error fetching activity streams: {error_message}"

    # Format the response
    if not result:
        return f"No stream data found for activity {activity_id}."

    # Ensure result is a list
    streams = result if isinstance(result, list) else []

    if not streams:
        return f"No stream data found for activity {activity_id}."

    # Format the streams data
    streams_summary = f"Activity Streams for {activity_id}:\n\n"

    for stream in streams:
        if not isinstance(stream, dict):
            continue

        stream_type = stream.get("type", "unknown")
        stream_name = stream.get("name", stream_type)
        data = stream.get("data", [])
        value_type = stream.get("valueType", "")

        streams_summary += f"Stream: {stream_name} ({stream_type})\n"
        streams_summary += f"  Value Type: {value_type}\n"
        streams_summary += f"  Data Points: {len(data)}\n"

        # Show first few and last few data points for preview
        if data:
            if len(data) <= 10:
                streams_summary += f"  Values: {data}\n"
            else:
                preview_start = data[:5]
                preview_end = data[-5:]
                streams_summary += f"  First 5 values: {preview_start}\n"
                streams_summary += f"  Last 5 values: {preview_end}\n"

        streams_summary += "\n"

    return streams_summary


@mcp.tool()
async def get_activity_messages(
    athlete_name: str,
    activity_id: str,
) -> str:
    """Get messages (notes/comments) for a specific activity from Intervals.icu

    Args:
        athlete_name: Name of the athlete as configured in athletes.json.
        activity_id: The Intervals.icu activity ID.
    """
    try:
        _athlete_id, api_key = get_athlete_credentials(athlete_name)
    except ValueError as e:
        return str(e)
    result = await make_intervals_request(
        url=f"/activity/{activity_id}/messages",
        api_key=api_key,
    )

    if isinstance(result, dict) and "error" in result:
        error_message = result.get("message", "Unknown error")
        return f"Error fetching activity messages: {error_message}"

    if not result:
        return f"No messages found for activity {activity_id}."

    messages = result if isinstance(result, list) else []
    if not messages:
        return f"No messages found for activity {activity_id}."

    output = f"Messages for activity {activity_id}:\n\n"
    for msg in messages:
        if isinstance(msg, dict):
            output += format_activity_message(msg) + "\n\n"

    return output


@mcp.tool()
async def add_activity_message(
    athlete_name: str,
    activity_id: str,
    content: str,
) -> str:
    """Add a message (note/comment) to an activity on Intervals.icu

    Args:
        athlete_name: Name of the athlete as configured in athletes.json.
        activity_id: The Intervals.icu activity ID.
        content: The message text to add.
    """
    try:
        _athlete_id, api_key = get_athlete_credentials(athlete_name)
    except ValueError as e:
        return str(e)
    result = await make_intervals_request(
        url=f"/activity/{activity_id}/messages",
        api_key=api_key,
        method="POST",
        data={"content": content},
    )

    if isinstance(result, dict) and "error" in result:
        error_message = result.get("message", "Unknown error")
        return f"Error adding message to activity: {error_message}"

    if not result or not isinstance(result, dict):
        return "Error: Unexpected response when adding message."

    msg_id = result.get("id")
    if msg_id is not None:
        return f"Successfully added message (ID: {msg_id}) to activity {activity_id}."
    return f"Message appears to have been added to activity {activity_id}, but no ID was returned. Please verify manually."
