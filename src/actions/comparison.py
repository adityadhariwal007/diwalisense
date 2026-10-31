"""Location-based Diwali comparison. PM2.5 sub-index is not full official AQI."""
from functools import lru_cache
import math
from pathlib import Path
import numpy as np
import pandas as pd
from src.features.hourly import hourly_features
from src.models.hourly import predict

ROOT = Path(__file__).resolve().parents[2]
DAYS = [('Before Diwali', '2025-10-19'), ('Diwali', '2025-10-20'), ('After Diwali', '2025-10-21')]


def pm25_aqi(value):
    if value is None or not math.isfinite(value) or value < 0:
        return None
    concentration = math.floor(value + 0.5)
    # CPCB publishes an open-ended severe concentration band; don't invent an exact index there.
    if concentration > 250:
        return {'value': None, 'display': '401–500', 'label': 'Severe', 'tone': 'severe'}
    bands = [(0, 30, 0, 50, 'Good', 'good'), (31, 60, 51, 100, 'Satisfactory', 'fair'),
             (61, 90, 101, 200, 'Moderate', 'moderate'), (91, 120, 201, 300, 'Poor', 'poor'),
             (121, 250, 301, 400, 'Very poor', 'very-poor')]
    for lo, hi, index_lo, index_hi, label, tone in bands:
        if lo <= concentration <= hi:
            index = round(index_lo + (concentration - lo) * (index_hi - index_lo) / (hi - lo))
            return {'value': index, 'display': str(index), 'label': label, 'tone': tone}


def cigarette_comparison(pm25):
    if pm25 is None or not math.isfinite(pm25) or pm25 < 0:
        return None
    per_day = pm25 / 22
    return {'day': round(per_day, 1), 'week': round(per_day * 7, 1), 'year': round(per_day * 365, 1)}


def distances_km(latitude, longitude, stations):
    latitudes = np.radians(stations.latitude.to_numpy(dtype=float))
    longitudes = np.radians(stations.longitude.to_numpy(dtype=float))
    lat, lon = np.radians([latitude, longitude])
    a = np.sin((latitudes - lat) / 2) ** 2 + np.cos(lat) * np.cos(latitudes) * np.sin((longitudes - lon) / 2) ** 2
    return 6371 * 2 * np.arcsin(np.sqrt(np.clip(a, 0, 1)))


def day_window(day):
    end = (pd.Timestamp(day, tz='Asia/Kolkata') + pd.Timedelta(hours=23, minutes=30)).tz_convert('UTC')
    return end - pd.Timedelta(hours=24), end


@lru_cache(maxsize=1)
def source_hours():
    return pd.read_parquet(ROOT / 'data/processed/training_package/holdout_2025.parquet')


def nearby_station(latitude, longitude, stations, source):
    candidates = stations.dropna(subset=['latitude', 'longitude']).copy()
    candidates['distance_km'] = distances_km(latitude, longitude, candidates)
    candidates = candidates.sort_values('distance_km')
    candidates = candidates[candidates.distance_km <= 35]
    if candidates.empty:
        raise ValueError('We only have Delhi data. Choose a Delhi area or try the Delhi demo.')
    # Keep the same nearby source for all three days; never silently compare different locations.
    for _, station in candidates.iterrows():
        rows = source[source.station_id == station.station_id]
        complete = all(rows.loc[rows.time.ge(day_window(day)[0]) & rows.time.lt(day_window(day)[1]), 'pm25'].count() >= 16 for _, day in DAYS)
        if complete:
            return station
    return candidates.iloc[0]


@lru_cache(maxsize=48)
def station_comparison(station_id, artifact_path):
    import joblib
    bundle = joblib.load(artifact_path)
    source = source_hours()
    start, _ = day_window(DAYS[0][1])
    _, end = day_window(DAYS[-1][1])
    frame = source[(source.station_id == station_id) & source.time.between(start - pd.Timedelta(hours=72), end)].copy()
    features = (hourly_features(frame, bundle['stations'], sample_every_hours=1, require_target=False)
                if not frame.empty else pd.DataFrame())
    if not features.empty:
        quantiles, _, _ = predict(bundle['models'], features)
        features['prediction'] = quantiles[:, 1]
    phases = []
    for label, day in DAYS:
        lo, hi = day_window(day)
        observed = frame.loc[frame.time.ge(lo) & frame.time.lt(hi), 'pm25'].dropna()
        predicted = features.loc[features.time.ge(lo) & features.time.lt(hi), 'prediction'] if 'prediction' in features else pd.Series(dtype=float)
        values = {'label': label, 'date': day, 'observed_hours': len(observed), 'predicted_hours': len(predicted)}
        for name, series in [('recorded', observed), ('estimated', predicted)]:
            value = float(series.mean()) if len(series) >= 16 else None
            values[name] = {'pm25': round(value, 1) if value is not None else None,
                            'aqi': pm25_aqi(value), 'cigarettes': cigarette_comparison(value)}
        phases.append(values)
    return phases
