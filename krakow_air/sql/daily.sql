WITH hours AS (
    SELECT generate_series(
        CAST(:start AS date)::timestamp AT TIME ZONE 'Europe/Warsaw',
        (CAST(:end AS date) + 1)::timestamp AT TIME ZONE 'Europe/Warsaw' - interval '1 hour',
        interval '1 hour'
    ) AS valid_at
), daily AS (
    SELECT (h.valid_at AT TIME ZONE 'Europe/Warsaw')::date AS day,
           count(*) AS expected_hours,
           count(o.valid_at) AS observed_hours,
           count(*) - count(o.valid_at) AS missing_hours,
           100.0 * count(o.valid_at) / count(*) AS completeness_pct,
           avg(o.pm2_5) AS pm25_mean, max(o.pm2_5) AS pm25_peak,
           avg(o.pm10) AS pm10_mean, max(o.pm10) AS pm10_peak,
           avg(o.european_aqi) AS aqi_mean, max(o.european_aqi) AS aqi_peak
    FROM hours h
    LEFT JOIN krakow_hourly o USING (valid_at)
    GROUP BY 1
)
SELECT daily.*,
       CASE WHEN observed_hours = 0 THEN 'Missing'
            WHEN missing_hours > 0 THEN 'Partial'
            ELSE 'Complete' END AS day_status,
       CASE WHEN missing_hours = 0 AND lag(missing_hours) OVER w = 0
            THEN pm25_mean - lag(pm25_mean) OVER w END AS pm25_change,
       CASE WHEN missing_hours = 0 AND lag(missing_hours) OVER w = 0
            THEN pm10_mean - lag(pm10_mean) OVER w END AS pm10_change,
       CASE WHEN missing_hours = 0 AND lag(missing_hours) OVER w = 0
            THEN aqi_mean - lag(aqi_mean) OVER w END AS aqi_change
FROM daily
WINDOW w AS (ORDER BY day)
ORDER BY day
