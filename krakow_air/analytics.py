from datetime import date
from importlib.resources import files

import pandas as pd
from sqlalchemy import func, inspect, select, text

from .storage import observations


def available_dates(engine):
    with engine.connect() as conn:
        if not inspect(conn).has_table(observations.name):
            return None
        stamp = observations.c.valid_at
        bounds = conn.execute(select(*(
            func.date(func.timezone("Europe/Warsaw", aggregate(stamp)))
            for aggregate in (func.min, func.max)
        ))).one()
        return tuple(bounds) if bounds[0] else None


def validate_dates(start, end):
    if type(start) is not date or type(end) is not date:
        raise ValueError("Select both a start date and an end date.")
    if start > end:
        raise ValueError("The start date must be on or before the end date.")


def daily_report(engine, start, end):
    validate_dates(start, end)
    sql = files("krakow_air").joinpath("sql", "daily.sql").read_text(encoding="utf-8")
    with engine.connect() as conn:
        return pd.read_sql_query(text(sql), conn, params={"start": start, "end": end})
