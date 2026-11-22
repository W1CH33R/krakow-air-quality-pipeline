import math
from datetime import UTC, date, datetime, time, timedelta

from .source import FIELDS


def validate(payload: dict, day: date) -> list[dict]:
    """Reject the whole day if the response cannot support a complete hourly series."""
    if not isinstance(payload, dict) or payload.get("utc_offset_seconds") != 0:
        raise ValueError("Expected a UTC hourly response")
    units = payload.get("hourly_units")
    hourly = payload.get("hourly")
    if not isinstance(units, dict) or not isinstance(hourly, dict):
        raise ValueError("Missing hourly data or units")
    for field, unit in zip(FIELDS, ("μg/m³", "μg/m³", "EAQI"), strict=True):
        if units.get(field) != unit:
            raise ValueError(f"Unexpected unit for {field}")
    for field in ("time", *FIELDS):
        if not isinstance(hourly.get(field), list) or len(hourly[field]) != 24:
            raise ValueError(f"Expected 24 hourly values for {field}")
    start = datetime.combine(day, time.min, tzinfo=UTC)
    rows = []
    for hour, stamp in enumerate(hourly["time"]):
        expected = start + timedelta(hours=hour)
        if stamp != expected.strftime("%Y-%m-%dT%H:%M"):
            raise ValueError(f"Unexpected timestamp at hour {hour}")
        row = {"valid_at": expected}
        for field in FIELDS:
            value = hourly[field][hour]
            if type(value) not in (float, int) or not math.isfinite(value) or value < 0:
                raise ValueError(f"Invalid {field} at {stamp}")
            row[field] = value
        rows.append(row)
    return rows
