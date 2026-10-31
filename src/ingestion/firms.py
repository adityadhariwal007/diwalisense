"""Count satellite detections, not unique fires or confirmed crop burning."""
import os
from datetime import date
from io import StringIO

import pandas as pd
import requests
from dotenv import load_dotenv


def fetch_fire_counts(start_date, days=1, bbox="73,27,78,32", source="VIIRS_SNPP_SP"):
    load_dotenv()
    key = os.getenv("FIRMS_MAP_KEY")
    if not key:
        raise ValueError("Set FIRMS_MAP_KEY in .env")
    date.fromisoformat(start_date)
    if not 1 <= days <= 5:
        raise ValueError("FIRMS accepts 1 to 5 days per area request")
    # TODO: verify product availability for the requested dates in FIRMS docs.
    url = f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{key}/{source}/{bbox}/{days}/{start_date}"
    try:
        response = requests.get(url, timeout=60)
        response.raise_for_status()
    except requests.RequestException:
        # The credential is in the URL: do not include it in errors or logs.
        raise RuntimeError("FIRMS request failed; check key, limits and availability") from None
    if not response.text.strip():
        raise ValueError("Empty FIRMS response; do not interpret as zero fires")
    frame = pd.read_csv(StringIO(response.text))
    if "acq_date" not in frame:
        raise ValueError("Unexpected FIRMS response; verify product/date availability")
    dates = pd.date_range(start_date, periods=days, freq="D")
    observed_dates = pd.to_datetime(frame["acq_date"], errors="raise")
    counts = observed_dates.value_counts().reindex(dates, fill_value=0)
    return counts.rename_axis("date").rename("fire_detections").reset_index()
