import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from src.features.hourly import FEATURES, hourly_features
from api.main import app, MODEL_PATH


def sample():
    time = pd.date_range('2024-01-01', periods=100, freq='h', tz='UTC')
    rows = pd.DataFrame({'time': time, 'station_id': 'a', 'pm25': np.arange(100, dtype=float),
        'available_no_earlier_than': time + pd.Timedelta(hours=1),
        'wind_speed_10m': 2., 'boundary_layer_height': 100., 'temperature_2m': 20., 'relative_humidity_2m': 60.})
    meta = pd.DataFrame({'station_id': ['a'], 'latitude': [28.6], 'longitude': [77.2]})
    return rows, meta


def test_hourly_features_use_only_available_past_bins():
    rows, meta = sample()
    features = hourly_features(rows, meta)
    target = rows.loc[84, 'time']
    at_target = features[features.time == target].iloc[0]
    assert at_target.pm25_lag6 == 77
    assert at_target.input_available_at == target - pd.Timedelta(hours=6)
    changed = rows.copy()
    changed.loc[78:, ['pm25', 'wind_speed_10m', 'temperature_2m']] = 999
    again = hourly_features(changed, meta)
    pd.testing.assert_series_equal(at_target[FEATURES], again[again.time == target].iloc[0][FEATURES])
    rows.loc[77, 'pm25'] = np.nan
    assert target not in hourly_features(rows, meta).time.tolist()


def test_bad_availability_and_duplicates_fail():
    rows, meta = sample()
    with pytest.raises(ValueError, match='Duplicate'):
        hourly_features(pd.concat([rows, rows.iloc[:1]]), meta)
    rows.loc[77, 'available_no_earlier_than'] = rows.loc[84, 'time']
    with pytest.raises(ValueError, match='availability'):
        hourly_features(rows, meta)


@pytest.mark.skipif(not MODEL_PATH.exists(), reason='Train the real-data artifact before integration checks')
def test_real_forecast_and_input_validation():
    client = TestClient(app)
    response = client.get('/forecast')
    assert response.status_code == 200, response.text
    result = response.json()
    assert result['is_dummy'] is False and result['is_live'] is False
    assert 0 <= result['p10'] <= result['p50'] <= result['p90']
    assert pd.Timestamp(result['local_time']) - pd.Timestamp(result['issue_time']) == pd.Timedelta(hours=6)
    assert result['series']
    assert client.get('/forecast', params={'date': '2026-11-01'}).status_code == 422
    assert client.get('/forecast', params={'hour': 3}).status_code == 422
    assert client.get('/forecast', params={'station': 'invented ward'}).status_code == 404
    priorities = client.get('/priorities').json()['priorities']
    assert [row['p50'] for row in priorities] == sorted([row['p50'] for row in priorities], reverse=True)
