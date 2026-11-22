from datetime import date, timedelta

import pandas as pd
import pytest

from krakow_air.analytics import available_dates, daily_report, validate_dates
from krakow_air.storage import metadata, save
from krakow_air.transform import validate


@pytest.mark.parametrize("start,end", [
    (None, date.today()), (date.today(), None), ("2025-01-01", date.today()),
    (date(2025, 1, 2), date(2025, 1, 1)),
])
def test_invalid_range(start, end):
    with pytest.raises(ValueError):
        validate_dates(start, end)


@pytest.mark.integration
@pytest.mark.parametrize("day,hours", [(date(2025, 3, 30), 23), (date(2025, 10, 26), 25)])
def test_dst_and_empty_database(engine, day, hours):
    assert available_dates(engine) is None
    metadata.create_all(engine)
    assert available_dates(engine) is None
    row = daily_report(engine, day, day).iloc[0]
    assert row.expected_hours == row.missing_hours == hours
    assert row.observed_hours == row.completeness_pct == 0
    assert pd.isna(row.pm25_mean)


@pytest.mark.integration
def test_local_days_peaks_changes_and_gaps(engine, day, payload):
    rows = validate(payload, day)
    rows[-1].update(pm2_5=12.5, pm10=24, european_aqi=60)
    rows[0].update(pm10=27)
    save(rows, engine)
    tomorrow = day + timedelta(days=1)
    assert available_dates(engine) == (day, tomorrow)
    frame = daily_report(engine, day - timedelta(days=1), tomorrow + timedelta(days=1))
    assert list(frame.observed_hours) == [0, 23, 1, 0]
    assert list(frame.missing_hours) == [24, 1, 23, 24]
    first, second = frame.iloc[1], frame.iloc[2]
    assert first.completeness_pct == pytest.approx(100 * 23 / 24)
    assert first.pm10_mean == 5
    assert first.pm10_peak == 27
    assert first.pm25_peak == first.pm25_mean == 2.5
    assert second.aqi_peak == second.aqi_mean == 60
    assert list(frame.day_status) == ["Missing", "Partial", "Partial", "Missing"]
    assert frame[["pm25_change", "pm10_change", "aqi_change"]].isna().all(axis=None)
    assert pd.isna(first.pm25_change)
    assert pd.isna(frame.iloc[-1].aqi_mean)
    assert daily_report(engine, tomorrow, tomorrow).iloc[0].observed_hours == 1


@pytest.mark.integration
def test_trends_require_two_adjacent_complete_days(engine, day, payload):
    rows = validate(payload, day)
    for offset in range(3):
        save([{**row, "valid_at": row["valid_at"] + timedelta(days=offset),
               "pm2_5": offset, "pm10": 2 * offset, "european_aqi": 3 * offset}
              for row in rows], engine)
    frame = daily_report(engine, day, day + timedelta(days=3))
    assert list(frame.day_status) == ["Partial", "Complete", "Complete", "Partial"]
    for column, delta in [("pm25_change", 1), ("pm10_change", 2), ("aqi_change", 3)]:
        assert frame[column].iloc[2] == pytest.approx(delta)
        assert frame[column].iloc[[0, 1, 3]].isna().all()
