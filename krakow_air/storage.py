import os

from sqlalchemy import (
    URL, CheckConstraint, Column, DateTime, Float, MetaData, Table, create_engine, func,
    or_, select,
)
from sqlalchemy.dialects.postgresql import insert

metadata = MetaData()
observations = Table(
    "krakow_hourly", metadata,
    Column("valid_at", DateTime(timezone=True), primary_key=True),
    Column("pm2_5", Float, nullable=False),
    Column("pm10", Float, nullable=False),
    Column("european_aqi", Float, nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    CheckConstraint("pm2_5 >= 0 AND pm10 >= 0 AND european_aqi >= 0"),
)


def database_url():
    if url := os.getenv("DATABASE_URL"):
        return url
    if not (password := os.getenv("POSTGRES_PASSWORD")):
        raise ValueError("Set POSTGRES_PASSWORD or DATABASE_URL for ingestion")
    return URL.create("postgresql+psycopg", username="air", password=password,
                      host=os.getenv("POSTGRES_HOST", "localhost"), database="air")


def save(rows, engine):
    with engine.begin() as conn:
        # Serialize table bootstrap and overlapping loads for this single-city dataset.
        conn.execute(select(func.pg_advisory_xact_lock(506471994)))
        metadata.create_all(conn)
        stmt = insert(observations).values(rows)
        metrics = {key: stmt.excluded[key] for key in ("pm2_5", "pm10", "european_aqi")}
        changed = or_(*(observations.c[k] != v for k, v in metrics.items()))
        result = conn.execute(stmt.on_conflict_do_update(
            index_elements=[observations.c.valid_at],
            set_={**metrics, "updated_at": func.now()}, where=changed,
        ).returning(observations.c.valid_at))
        return len(result.all())


def load(rows):
    engine = create_engine(database_url(), hide_parameters=True)
    try:
        return save(rows, engine)
    finally:
        engine.dispose()
