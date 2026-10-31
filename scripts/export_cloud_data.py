"""Export daily history and existing-model snapshots; never train or replace a model."""
import json
from pathlib import Path
import joblib
import pandas as pd
from src.actions.comparison import station_comparison
ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / 'data/processed/multiyear_training'

def main():
    bundle = joblib.load(ROOT / 'artifacts/hourly_model.joblib')
    stations = []
    snapshots = []
    for _, row in bundle['stations'].dropna(subset=['latitude', 'longitude']).iterrows():
        station = {'station_id': row.station_id, 'name': row.station_name.split(',')[0].strip(),
                   'latitude': float(row.latitude), 'longitude': float(row.longitude)}
        stations.append(station)
        phases = station_comparison(row.station_id, str(ROOT / 'artifacts/hourly_model.joblib'))
        snapshots.append({'station_id': row.station_id, 'year': 2025, 'phases': phases,
                          'complete': all(p['observed_hours'] >= 16 for p in phases),
                          'model_version': '2024-prototype', 'is_live': False})
    daily = []
    for year in range(2017, 2026):
        path = PACKAGE / (f'station_observations_{year}.parquet' if year < 2025 else 'opencity_holdout_2025.parquet')
        frame = pd.read_parquet(path)
        frame['date'] = frame.observation_time_utc.dt.tz_convert('Asia/Kolkata').dt.strftime('%Y-%m-%d')
        grouped = frame.groupby(['station_id', 'date']).pm25.agg(['mean', 'count']).reset_index()
        grouped = grouped[grouped['count'] >= 16]
        for row in grouped.itertuples(index=False):
            daily.append({'station_id': row.station_id, 'date': row.date, 'pm25': round(row.mean, 3),
                          'readings': row.count, 'source': 'XKDR/CPCB' if year < 2025 else 'OpenCity/CPCB'})
    result = {'stations': stations, 'snapshots': snapshots, 'daily_air': daily}
    assert len(stations) == len(snapshots) and len({s['station_id'] for s in stations}) == len(stations)
    assert all(row['readings'] >= 16 and row['pm25'] >= 0 for row in daily)
    output = ROOT / '.presentation-build/cloud-data.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, allow_nan=False))
    print({key: len(value) for key, value in result.items()})

if __name__ == '__main__':
    main()
