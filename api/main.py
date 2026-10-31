from datetime import date as Date
from functools import lru_cache
from pathlib import Path
import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from src.actions.comparison import nearby_station, source_hours, station_comparison
from src.models.hourly import predict

ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = ROOT / 'artifacts/hourly_model.joblib'
app = FastAPI(title='DiwaliSense', version='0.2.0')


@lru_cache(maxsize=1)
def model_bundle():
    if not MODEL_PATH.exists():
        raise HTTPException(503, 'Model not trained. Run python -m src.models.hourly, then restart the API.')
    # Trust only our locally generated artifact, never an uploaded pickle.
    return joblib.load(MODEL_PATH)


@app.get('/health')
def health():
    return {'status': 'ready' if MODEL_PATH.exists() else 'model_missing', 'mode': 'historical_replay'}


@app.get('/stations')
def stations():
    bundle = model_bundle()
    names = bundle['stations'].set_index('station_id').station_name.to_dict()
    items = []
    for station, group in bundle['rows'].groupby('station_id'):
        local = group.time.dt.tz_convert('Asia/Kolkata')
        availability = {}
        for stamp in local:
            availability.setdefault(stamp.strftime('%Y-%m-%d'), []).append(stamp.hour)
        items.append({'id': station, 'name': names.get(station, station), 'availability': availability})
    return {'stations': items, 'mode': 'historical_replay', 'test_year': 2025, 'default_date': '2025-10-20'}


@app.get('/metrics')
def measured_metrics():
    return model_bundle()['report']


def forecast_for(station, date, hour):
    if hour not in [5, 11, 17, 23] or date.year != 2025:
        raise HTTPException(422, 'Select a 2025 date and an IST hour of 05:30, 11:30, 17:30 or 23:30.')
    bundle = model_bundle()
    rows = bundle['rows']
    if station not in bundle['report']['stations']:
        raise HTTPException(404, 'Unknown station. Choose an entry from /stations.')
    target = (pd.Timestamp(date, tz='Asia/Kolkata') + pd.Timedelta(hours=hour, minutes=30)).tz_convert('UTC')
    selected = rows[(rows.station_id == station) & (rows.time == target)]
    if selected.empty:
        raise HTTPException(422, 'This station/time has missing target or prior observations. Choose another time or station.')
    window = rows[(rows.station_id == station) & rows.time.between(target - pd.Timedelta(hours=24), target + pd.Timedelta(hours=24))].copy()
    quantiles, baseline, adjustment = predict(bundle['models'], window)
    series = []
    for i, (_, row) in enumerate(window.iterrows()):
        series.append({'time': row.time.isoformat(), 'local_time': row.time.tz_convert('Asia/Kolkata').isoformat(),
                       'issue_time': row.issue_time.tz_convert('Asia/Kolkata').isoformat(),
                       'p10': round(float(quantiles[i, 0]), 1), 'p50': round(float(quantiles[i, 1]), 1),
                       'p90': round(float(quantiles[i, 2]), 1), 'baseline': round(float(baseline[i]), 1),
                       'diwali_adjustment': round(float(adjustment[i]), 1),
                       'observed': round(float(row.pm25), 1), 'persistence': round(float(row.pm25_lag6), 1),
                       'is_event_period': bool(row.event)})
    result = next(item for item in series if item['time'] == target.isoformat())
    meta = bundle['stations'].set_index('station_id').loc[station]
    return {**result, 'station': station, 'station_name': meta.station_name,
            'latitude': float(meta.latitude), 'longitude': float(meta.longitude),
            'units': 'µg/m³', 'mode': 'historical_replay', 'is_dummy': False, 'is_live': False,
            'horizon_hours': 6, 'confidence': 'Experimental; see holdout interval coverage.',
            'range_note': 'P10–P90 model estimates expanded using pooled December 2024 calibration errors.',
            'advice': 'Compare with official reports before decisions. No safe cracker-use time is identified.',
            'series': series, 'series_note': 'Each point is a separate six-hour-ahead replay, not one multi-day forecast.',
            'source': 'OpenCity Delhi 2024–2025 processed package; see repository data quality audit.'}


@app.get('/forecast')
def forecast(station: str = Query(default='site_5024', min_length=1, max_length=100),
             date: Date = Date(2025, 10, 20), hour: int = Query(default=23, ge=0, le=23)):
    return forecast_for(station, date, hour)


@app.get('/priorities')
def priorities(date: Date = Date(2025, 10, 20), hour: int = Query(default=23, ge=0, le=23)):
    if date.year != 2025 or hour not in [5, 11, 17, 23]:
        raise HTTPException(422, 'Select an available 2025 date and replay hour.')
    results, missing = [], []
    for station in model_bundle()['report']['stations']:
        try:
            result = forecast_for(station, date, hour)
            results.append({key: result[key] for key in ['station', 'station_name', 'p10', 'p50', 'p90']})
        except HTTPException as error:
            if error.status_code != 422:
                raise
            missing.append(station)
    return {'priorities': sorted(results, key=lambda row: row['p50'], reverse=True),
            'missing_stations': missing, 'note': 'Station-area review order; not ward estimates or validated intervention recommendations.'}


class LocationRequest(BaseModel):
    latitude: float = Field(ge=-90, le=90, allow_inf_nan=False)
    longitude: float = Field(ge=-180, le=180, allow_inf_nan=False)


@app.get('/locations')
def locations():
    stations = model_bundle()['stations']
    areas = []
    seen = set()
    for _, station in stations.dropna(subset=['latitude', 'longitude']).iterrows():
        name = station.station_name.split(',')[0].strip()
        if name in seen:
            continue
        seen.add(name)
        areas.append({'name': name, 'latitude': float(station.latitude), 'longitude': float(station.longitude)})
    return sorted(areas, key=lambda area: area['name'])


@app.post('/comparison')
def comparison(location: LocationRequest):
    try:
        station = nearby_station(location.latitude, location.longitude, model_bundle()['stations'], source_hours())
    except ValueError as error:
        raise HTTPException(404, str(error)) from error
    return {
        'area': station.station_name.split(',')[0], 'distance_km': round(float(station.distance_km), 1),
        'year': 2025, 'is_live': False,
        'phases': station_comparison(station.station_id, str(MODEL_PATH)),
        'details': {
            'station_name': station.station_name, 'station_id': station.station_id,
            'aqi': 'PM2.5 sub-index estimate only; not full official AQI. Severe is shown as a band, not an invented exact number.',
            'daily_window': '24 hours ending at 23:30 IST on the displayed date. At least 16 hourly values required.',
            'model': 'AI daily values average separate six-hour-ahead hourly predictions, not one day-ahead forecast. Daily AQI accuracy has not been evaluated.',
            'exposure': 'Daily PM2.5 / 22 is a rough Berkeley Earth comparison, not personal smoking or medical risk. Week/year assume unchanged daily pollution.',
            'location': 'One nearby monitoring location is used across all days. It is not a measurement at the user’s home.',
        },
    }


if (ROOT / 'frontend/dist').exists():
    app.mount('/', StaticFiles(directory=ROOT / 'frontend/dist', html=True), name='website')
