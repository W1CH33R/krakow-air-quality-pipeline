from datetime import date

import os
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text


@pytest.fixture
def day():
    return date(2024, 1, 2)


@pytest.fixture
def payload(day):
    """Synthetic contract fixture. Values are never exported as city data."""
    return {
        "utc_offset_seconds": 0,
        "hourly_units": {"pm2_5": "μg/m³", "pm10": "μg/m³", "european_aqi": "EAQI"},
        "hourly": {
            "time": [f"{day}T{h:02}:00" for h in range(24)],
            "pm2_5": [2.5] * 24, "pm10": [4.0] * 24, "european_aqi": [110] * 24,
        },
    }


@pytest.fixture
def engine():
    url = os.getenv("TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set TEST_DATABASE_URL to run PostgreSQL integration tests")
    admin = create_engine(url)
    schema = "test_" + uuid4().hex
    with admin.begin() as conn:
        conn.execute(text(f"CREATE SCHEMA {schema}"))
    db = create_engine(url, connect_args={"options": f"-c search_path={schema}"})
    try:
        yield db
    finally:
        db.dispose()
        with admin.begin() as conn:
            conn.execute(text(f"DROP SCHEMA {schema} CASCADE"))
        admin.dispose()
