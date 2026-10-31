"""Historical weather only; not an operational forecast adapter."""
from datetime import date

import pandas as pd
import requests


def fetch_weather(latitude, longitude, start_date, end_date):
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        raise ValueError("Invalid coordinates")
    if date.fromisoformat(start_date) > date.fromisoformat(end_date):
        raise ValueError("start_date must precede end_date")
    variables = ["temperature_2m", "relative_humidity_2m",
                 "wind_speed_10m", "boundary_layer_height"]
    response = requests.get(
        "https://archive-api.open-meteo.com/v1/archive",
        params={"latitude": latitude, "longitude": longitude,
                "start_date": start_date, "end_date": end_date,
                "hourly": ",".join(variables), "timezone": "UTC",
                "wind_speed_unit": "ms"},
        timeout=60,
    )
    response.raise_for_status()
    frame = pd.DataFrame(response.json()["hourly"])
    if frame.empty or any(v not in frame or frame[v].isna().all() for v in variables):
        raise ValueError("Weather variable unavailable; check endpoint/model docs")
    frame["time"] = pd.to_datetime(frame["time"], utc=True)
    return frame  # Wind: m/s; mixing height: m. Preserve partial gaps.
