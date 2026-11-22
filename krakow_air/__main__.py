import argparse
import json
import logging
from datetime import UTC, date, datetime, timedelta

from .source import fetch
from .transform import validate


def main():
    today = datetime.now(UTC).date()
    parser = argparse.ArgumentParser(description="Ingest one completed UTC day for Krakow")
    parser.add_argument("--date", type=date.fromisoformat, default=today - timedelta(days=1))
    parser.add_argument("--preview", action="store_true", help="Print validated JSON to stdout")
    args = parser.parse_args()
    if args.date >= today:
        parser.error("Choose a completed UTC day")
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    try:
        rows = validate(fetch(args.date), args.date)
        if args.preview:
            print(json.dumps(rows, default=lambda value: value.isoformat(), indent=2))
        else:
            from .storage import load

            changed = load(rows)
            logging.info("day=%s validated=%d inserted_or_updated=%d", args.date, len(rows), changed)
    except Exception as exc:
        # Connection errors can include connection details. Keep credentials out of logs.
        from urllib.error import HTTPError

        if isinstance(exc, (ValueError, HTTPError)):
            logging.error("day=%s %s", args.date, exc)
        else:
            logging.error("day=%s ingestion failed (%s)", args.date, type(exc).__name__)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
