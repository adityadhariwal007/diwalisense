"""Fetch hourly PM2.5 within an approximate Delhi bounding box."""
import os

import pandas as pd
import requests
from dotenv import load_dotenv

BASE_URL = "https://api.openaq.org/v3"


def _pages(session, path, params):
    page = 1
    while True:
        response = session.get(
            BASE_URL + path, params={**params, "limit": 100, "page": page},
            timeout=60,
        )
        response.raise_for_status()  # Fail visibly on 401/429; do not return partial success.
        rows = response.json()["results"]
        yield from rows
        if len(rows) < 100:
            break
        page += 1


def fetch_delhi_pm25(start, end):
    """start/end: explicit timezone-aware timestamps; local interval is [start, end)."""
    load_dotenv()
    key = os.getenv("OPENAQ_API_KEY")
    if not key:
        raise ValueError("Set OPENAQ_API_KEY in .env")
    start, end = pd.Timestamp(start), pd.Timestamp(end)
    if start.tzinfo is None or end.tzinfo is None or start >= end:
        raise ValueError("Provide ordered timezone-aware start/end timestamps")
    records = []
    with requests.Session() as session:
        session.headers["X-API-Key"] = key
        locations = _pages(session, "/locations", {
            "bbox": "76.8,28.3,77.5,29.0", "iso": "IN", "mobile": "false",
        })
        for station in locations:
            for sensor in station["sensors"]:
                if sensor["parameter"]["name"] != "pm25":
                    continue
                hours = _pages(session, f"/sensors/{sensor['id']}/hours", {
                    "datetime_from": start.isoformat(), "datetime_to": end.isoformat(),
                })
                for row in hours:
                    period = row.get("period") or {}
                    if not period.get("datetimeFrom") or not period.get("datetimeTo"):
                        raise ValueError("Hourly period missing; verify OpenAQ schema")
                    time = pd.Timestamp(period["datetimeFrom"]["utc"])
                    if start <= time < end:
                        records.append({
                            "station_id": station["id"], "sensor_id": sensor["id"],
                            "time": time, "pm25": row["value"],
                            "units": row["parameter"]["units"],
                            "has_flags": row["flagInfo"]["hasFlags"],
                            "period_end": period["datetimeTo"]["utc"],
                        })
    return pd.DataFrame(records, columns=[
        "station_id", "sensor_id", "time", "pm25", "units", "has_flags", "period_end",
    ])
    # TODO: cache metadata, audit coverage, review flags and units before modeling.
