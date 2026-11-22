"""Fetch one complete UTC day from the CAMS European domain."""
import json
import logging
import time
from datetime import date
from http.client import IncompleteRead
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen

ENDPOINT = "https://air-quality-api.open-meteo.com/v1/air-quality"
FIELDS = ("pm2_5", "pm10", "european_aqi")
LOG = logging.getLogger(__name__)


def fetch(day: date) -> dict:
    query = urlencode({
        "latitude": 50.0647, "longitude": 19.9450, "domains": "cams_europe",
        "hourly": ",".join(FIELDS), "timezone": "GMT",
        "start_date": day.isoformat(), "end_date": day.isoformat(),
    })
    for attempt in range(1, 4):
        delay = 2 ** (attempt - 1)
        try:
            with urlopen(f"{ENDPOINT}?{query}", timeout=20) as response:
                return json.loads(response.read())
        except HTTPError as exc:
            exc.close()
            if exc.code not in {408, 429, 500, 502, 503, 504} or attempt == 3:
                raise
            retry_after = exc.headers.get("Retry-After", "")
            if retry_after.isdecimal():
                delay = max(delay, int(retry_after))
                if delay > 60:
                    raise
        except (URLError, TimeoutError, ConnectionError, IncompleteRead):
            if attempt == 3:
                raise
        LOG.warning("request failed day=%s attempt=%d retry_in_seconds=%d", day, attempt, delay)
        time.sleep(delay)
    raise AssertionError("unreachable")
