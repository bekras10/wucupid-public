"""Datetime formatting utilities."""
import pytz

def format_datetime_utc(dt):
    """
    Format a datetime in ISO8601 format with UTC timezone.
    Converts any timezone-aware datetime to UTC before formatting.
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        # If naive, assume it's in UTC
        dt = pytz.UTC.localize(dt)
    return dt.astimezone(pytz.UTC).isoformat()

def format_cycle_times(cycle):
    """Format all cycle times in UTC ISO8601 format."""
    return {
        "status": cycle.get("status"),
        "cycle_number": cycle.get("cycle_number"),
        "time_remaining": cycle.get("time_remaining"),
        "next_phase": cycle.get("next_phase"),
        "next_phase_date": format_datetime_utc(cycle.get("next_phase_date")),
        "survey_start_date": format_datetime_utc(cycle.get("survey_start_date")),
        "survey_end_date": format_datetime_utc(cycle.get("survey_end_date")),
        "processing_end_date": format_datetime_utc(cycle.get("processing_end_date"))
    } 