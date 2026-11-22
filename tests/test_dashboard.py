from pathlib import Path

import pytest
from sqlalchemy.exc import OperationalError
from streamlit.testing.v1 import AppTest

from krakow_air import analytics
from krakow_air.storage import save
from krakow_air.transform import validate

APP = Path(__file__).resolve().parents[1] / "krakow_air/dashboard.py"


def test_connection_failure(monkeypatch):
    def unavailable(engine):
        raise OperationalError("connect", None, Exception("private details"))

    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://localhost/test")
    monkeypatch.setattr(analytics, "available_dates", unavailable)
    app = AppTest.from_file(str(APP)).run(timeout=20)
    assert not app.exception
    assert "Unable to read" in app.error[0].value
    assert "private details" not in app.error[0].value


@pytest.mark.integration
def test_dashboard_filters(engine, day, payload, monkeypatch):
    from datetime import timedelta

    # Route dashboard reads to the isolated PostgreSQL schema used by the fixture.
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://localhost/test")
    load_bounds, load_daily = analytics.available_dates, analytics.daily_report
    monkeypatch.setattr(analytics, "available_dates", lambda _: load_bounds(engine))
    monkeypatch.setattr(analytics, "daily_report", lambda _, a, b: load_daily(engine, a, b))
    app = AppTest.from_file(str(APP)).run(timeout=20)
    assert "No observations yet" in app.info[0].value
    save(validate(payload, day), engine)
    app.run()
    assert not app.exception
    assert app.metric[3].value == "50.0%"
    assert len(app.dataframe[0].value) == 2
    assert not app.radio
    assert list(app.dataframe[0].value["Day status"]) == ["Partial", "Partial"]
    assert app.dataframe[0].value["Mean PM2.5"].isna().all()
    assert "0 of 2 local days are complete" in app.info[0].value
    assert not app.exception
    before = day - timedelta(days=1)
    app.date_input[0].set_value((before, before)).run()
    assert "No observations in this date range" in app.info[0].value
    app.date_input[0].set_value((day,)).run()
    assert "Select an end date" in app.info[0].value
