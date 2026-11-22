from datetime import timedelta

import altair as alt
import pandas as pd
import streamlit as st
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError

from krakow_air.analytics import available_dates, daily_report
from krakow_air.storage import database_url


@st.cache_resource
def database():
    return create_engine(database_url(), pool_pre_ping=True, connect_args={"connect_timeout": 5})


def chart(frame, metrics, unit):
    data = frame.rename(columns=metrics).melt(
        id_vars=["day", "segment"], value_vars=list(metrics.values()),
        var_name="Series", value_name="value",
    ).dropna(subset=["value"])
    plot = alt.Chart(data).mark_line(point=True).encode(
        x=alt.X("day:T", title="Local date", axis=alt.Axis(format="%d %b", tickMinStep=86_400_000, tickCount=8)),
        y=alt.Y("value:Q", title=unit, scale=alt.Scale(zero=True)),
        color=alt.Color("Series:N", scale=alt.Scale(range=["#087e83", "#b35428"]),
                        legend=alt.Legend(title=None, orient="top")),
        detail="segment:N",
        tooltip=[alt.Tooltip("day:T", title="Local date", format="%Y-%m-%d"),
                 "Series:N", alt.Tooltip("value:Q", title=unit, format=".1f")],
    ).interactive(bind_y=False)
    st.altair_chart(plot, width="stretch")


def main():
    st.set_page_config(page_title="Krakow Air Quality Intelligence", layout="wide")
    st.title("Krakow air quality")
    st.caption("Hourly CAMS model estimates via Open-Meteo · Krakow, Poland · Europe/Warsaw")
    try:
        db = database()
        bounds = available_dates(db)
        if bounds is None:
            st.info("No observations yet. Run the ingestion pipeline to load a completed UTC day.")
            return
        first, last = bounds
        selected = st.sidebar.date_input(
            "Local date range", (max(first, last - timedelta(days=29)), last),
            min_value=min(first, last - timedelta(days=365)), max_value=last,
        )
        st.sidebar.caption(f"Stored observations span {first} through {last}.")
        if len(selected) != 2:
            st.info("Select an end date to display the report.")
            return
        frame = daily_report(db, *selected)
    except (SQLAlchemyError, ValueError):
        st.error("Unable to read the database. Check the connection settings and PostgreSQL service.")
        return

    observed = int(frame.observed_hours.sum())
    expected = int(frame.expected_hours.sum())
    cols = st.columns(4)
    for col, metric, label in zip(cols, ["pm25_mean", "pm10_mean"], ["PM2.5", "PM10"]):
        value = (frame[metric] * frame.observed_hours).sum() / observed if observed else None
        col.metric(f"Observed-hour mean {label} (μg/m³)", f"{value:.1f}" if observed else "—")
    cols[2].metric("Peak European AQI", f"{frame.aqi_peak.max():.0f}" if observed else "—")
    cols[3].metric("Hourly coverage", f"{100 * observed / expected:.1f}%")
    st.caption(f"{observed:,} of {expected:,} expected hourly observations · "
               f"{expected - observed:,} missing")
    if observed:
        frame["day"] = pd.to_datetime(frame["day"])
        complete = frame.day_status.eq("Complete")
        if not complete.all():
            st.info(f"{int(complete.sum())} of {len(frame)} local days are complete. "
                    "Daily charts and mean comparisons use complete days only. "
                    "See Daily detail for coverage and observed peaks on other days.")
        frame["segment"] = (~complete).cumsum()
        frame.loc[~complete, ["pm25_mean", "pm10_mean", "aqi_mean"]] = float("nan")
        chart_days = frame.loc[complete]
    if observed and not chart_days.empty:
        pm, aqi = st.tabs(["Particulate matter", "European AQI"])
        with pm:
            mode = st.radio("Daily statistic", ["Mean", "Maximum"], horizontal=True)
            suffix = "mean" if mode == "Mean" else "peak"
            chart(chart_days, {f"pm25_{suffix}": "PM2.5", f"pm10_{suffix}": "PM10"}, "μg/m³")
        with aqi:
            chart(chart_days, {"aqi_mean": "Daily mean", "aqi_peak": "Daily maximum"}, "European AQI")
    elif not observed:
        st.info("No observations in this date range. Choose another range or load data.")
    st.subheader("Daily detail")
    st.caption("Changes compare daily means with the previous calendar day in the selected range. "
               "Both days must be complete. Peaks use available hours.")
    labels = {
        "day": "Local date", "day_status": "Day status", "expected_hours": "Expected hours", "observed_hours": "Observed hours",
        "missing_hours": "Missing hours", "completeness_pct": "Coverage (%)",
        "pm25_mean": "Mean PM2.5", "pm25_peak": "Peak PM2.5", "pm10_mean": "Mean PM10",
        "pm10_peak": "Peak PM10", "aqi_mean": "Mean AQI", "aqi_peak": "Peak AQI",
        "pm25_change": "PM2.5 change", "pm10_change": "PM10 change", "aqi_change": "AQI change",
    }
    st.dataframe(frame[list(labels)].rename(columns=labels).round(2), hide_index=True)


if __name__ == "__main__":
    main()
