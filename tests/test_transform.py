from datetime import UTC

import pytest

from krakow_air.transform import validate


def test_complete_day(day, payload):
    rows = validate(payload, day)
    assert len(rows) == 24
    assert rows[-1]["valid_at"].tzinfo is UTC
    assert rows[-1]["valid_at"].hour == 23
    assert rows[0]["european_aqi"] == 110


@pytest.mark.parametrize("bad", [None, -1, True, "3.0", float("inf"), float("nan")])
def test_invalid_value(day, payload, bad):
    payload["hourly"]["pm2_5"][3] = bad
    with pytest.raises(ValueError, match="pm2_5"):
        validate(payload, day)


@pytest.mark.parametrize("fault", ["gap", "duplicate", "unit", "offset", "missing"])
def test_invalid_contract(day, payload, fault):
    if fault == "gap":
        payload["hourly"]["pm10"].pop()
    elif fault == "duplicate":
        payload["hourly"]["time"][1] = payload["hourly"]["time"][0]
    elif fault == "unit":
        payload["hourly_units"]["pm10"] = "mg/m³"
    elif fault == "offset":
        payload["utc_offset_seconds"] = 3600
    else:
        del payload["hourly"]
    with pytest.raises(ValueError):
        validate(payload, day)
