"""Frozen 2024 development -> 2025 historical replay evaluation."""
import hashlib
import json
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from src.features.hourly import FEATURES, BURST_FEATURES, hourly_features
from src.models.baseline import train_baseline
from src.models.burst import train_burst

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / 'data/processed/training_package'


def metrics(y, prediction):
    error = np.asarray(y) - np.asarray(prediction)
    return {'n': len(error), 'mae': round(float(np.abs(error).mean()), 3),
            'rmse': round(float(np.sqrt(np.square(error).mean())), 3)}


def fit_models(train):
    normal = train[~train.event]
    baseline = train_baseline(normal[FEATURES], normal.pm25)
    earlier = normal[normal.time < '2024-10-01']
    events = train[train.event].copy()
    if len(events) < 30:
        raise ValueError('Insufficient event samples')
    earlier_models = train_baseline(earlier[FEATURES], earlier.pm25)
    prior_prediction = pd.Series(earlier_models[0.5].predict(events[FEATURES]), index=events.index)
    burst = train_burst(events[BURST_FEATURES], events.pm25, prior_prediction)
    return {'baseline': baseline, 'burst': burst, 'event_training_rows': len(events)}


def predict(models, rows):
    baseline = np.column_stack([models['baseline'][q].predict(rows[FEATURES]) for q in [0.1, 0.5, 0.9]])
    adjustment = np.zeros(len(rows))
    mask = rows.event.to_numpy()
    if mask.any():
        adjustment[mask] = models['burst'][0.5].predict(rows.loc[rows.event, BURST_FEATURES])
    quantiles = np.sort(np.maximum(0, baseline + adjustment[:, None]), axis=1)
    expansion = models.get('interval_expansion', 0)
    quantiles[:, 0] = np.maximum(0, quantiles[:, 0] - expansion)
    quantiles[:, 2] += expansion
    return quantiles, np.maximum(0, baseline[:, 1]), adjustment


def calibrated(train, calibration):
    models = fit_models(train)
    quantiles, _, _ = predict(models, calibration)
    scores = np.maximum(quantiles[:, 0] - calibration.pm25.to_numpy(), calibration.pm25.to_numpy() - quantiles[:, 2])
    level = min(1, np.ceil((len(scores) + 1) * 0.8) / len(scores))
    models['interval_expansion'] = max(0.0, float(np.quantile(scores, level, method='higher')))
    return models


def evaluate(models, rows):
    quantiles, baseline, _ = predict(models, rows)
    return {'model': metrics(rows.pm25, quantiles[:, 1]),
            'baseline_only': metrics(rows.pm25, baseline),
            'persistence': metrics(rows.pm25, rows.pm25_lag6),
            'interval_coverage': round(float(((rows.pm25 >= quantiles[:, 0]) & (rows.pm25 <= quantiles[:, 2])).mean()), 4)}


def main():
    station_meta = pd.read_csv(PACKAGE / 'stations.csv')
    development = pd.read_parquet(PACKAGE / 'development_2024.parquet')
    rows = hourly_features(development, station_meta)
    train = rows[rows.time < '2024-12-01']
    calibration = rows[rows.time >= '2024-12-01']
    models = calibrated(train, calibration)
    # Freeze decisions and fitted weights before opening any 2025 target values.
    artifacts = ROOT / 'artifacts'
    artifacts.mkdir(exist_ok=True)
    joblib.dump(models, artifacts / 'frozen_2024.joblib')
    frozen_hash = hashlib.sha256((artifacts / 'frozen_2024.joblib').read_bytes()).hexdigest()
    holdout = pd.read_parquet(PACKAGE / 'holdout_2025.parquet')
    test = hourly_features(holdout, station_meta)
    report = {
        'mode': 'historical_replay', 'frequency': 'hourly targets on a six-hour UTC schedule',
        'horizon_hours': 6, 'train_period': '2024 January–November',
        'calibration_period': 'December 2024', 'test_year': 2025,
        'frozen_model_sha256': frozen_hash, 'training_rows': len(train),
        'calibration_rows': len(calibration), 'test_rows': len(test),
        'stations': sorted(test.station_id.unique().tolist()),
        'event_training_rows': models['event_training_rows'], 'independent_training_diwalis': 1,
        'all_test': evaluate(models, test), 'diwali_test': evaluate(models, test[test.event]),
        'aqi_category_accuracy': '[TO BE MEASURED: hourly target is not 24-hour AQI]',
        'leave_one_station_out': {},
        'limitations': [
            'Historical six-hour-ahead replay, not a live 2026 forecast.',
            'Only one independent training Diwali (2024); stations are correlated event samples.',
            'Historical reanalysis and assumed bin-end availability; real reporting latency unknown.',
            '2024 timestamp interpretation supported on sampled days only; not provider-confirmed for every station/2025.',
            'Station holdout uses that station\'s prior pollution readings; not validation for unsensored wards.',
            '2017–2020 staging excluded until timezone and station crosswalk are resolved.',
            'No fires, road features, ban compliance or ward downscaling in this build.',
            'P10–P90 model estimates expanded using pooled December 2024 calibration; no event-specific coverage guarantee.',
        ],
    }
    for station in report['stations']:
        print(f'Leave-one-station-out: {station}', flush=True)
        fitted = calibrated(train[train.station_id != station], calibration[calibration.station_id != station])
        report['leave_one_station_out'][station] = evaluate(fitted, test[test.station_id == station])
    joblib.dump({'models': models, 'rows': test, 'report': report, 'stations': station_meta}, artifacts / 'hourly_model.joblib')
    (artifacts / 'metrics.json').write_text(json.dumps(report, indent=2))
    (ROOT / 'docs/measured_metrics.json').write_text(json.dumps(report, indent=2))
    print(json.dumps({'all_test': report['all_test'], 'diwali_test': report['diwali_test']}, indent=2))


if __name__ == '__main__':
    main()
