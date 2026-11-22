import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from krakow_air.storage import observations, save
from krakow_air.transform import validate


@pytest.mark.integration
def test_rerun_revision_and_rollback(engine, payload, day):
    rows = validate(payload, day)
    assert save(rows, engine) == 24
    assert save(rows, engine) == 0
    rows[0]["pm10"] = 9.0
    assert save(rows, engine) == 1
    rows[0]["pm10"] = 12.0
    rows[-1]["pm10"] = -1
    with pytest.raises(IntegrityError):
        save(rows, engine)
    with engine.connect() as conn:
        assert conn.scalar(select(func.count()).select_from(observations)) == 24
        assert conn.scalar(select(observations.c.pm10).order_by(observations.c.valid_at)) == 9.0
