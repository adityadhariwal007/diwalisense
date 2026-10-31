from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from api.main import app, MODEL_PATH
from src.actions.comparison import cigarette_comparison, day_window, distances_km, nearby_station, pm25_aqi


def test_pm25_index_and_exposure_do_not_invent_full_aqi_or_smoking():
    assert pm25_aqi(30)['value'] == 50
    assert pm25_aqi(31)['value'] == 51
    assert pm25_aqi(45)['value'] == 75
    assert pm25_aqi(60)['value'] == 100
    assert pm25_aqi(90)['value'] == 200
    assert pm25_aqi(120)['value'] == 300
    assert pm25_aqi(250)['value'] == 400
    assert pm25_aqi(600)['value'] is None
    assert pm25_aqi(600)['display'] == '401–500'
    assert pm25_aqi(float('nan')) is None
    assert pm25_aqi(-10) is None
    assert cigarette_comparison(22) == {'day': 1.0, 'week': 7.0, 'year': 365.0}
    assert cigarette_comparison(None) is None
    assert cigarette_comparison(0)['year'] == 0


def test_location_uses_one_nearby_complete_source_and_rejects_outside_coverage():
    stations = pd.DataFrame({'station_id': ['near', 'complete'], 'latitude': [28.6, 28.61], 'longitude': [77.2, 77.2]})
    hours = pd.date_range('2025-10-18T00:00Z', '2025-10-22T00:00Z', freq='h')
    source = pd.DataFrame({'station_id': 'complete', 'time': hours, 'pm25': 22.})
    assert distances_km(28.6, 77.2, stations)[0] == pytest.approx(0)
    chosen = nearby_station(28.6, 77.2, stations, source)
    assert chosen.station_id == 'complete'
    with pytest.raises(ValueError, match='Delhi'):
        nearby_station(30.3, 76.4, stations, source)
    start, end = day_window('2025-10-20')
    assert end - start == pd.Timedelta(hours=24)
    assert len(source[source.time.ge(start) & source.time.lt(end)]) == 24
    assert end.tz_convert('Asia/Kolkata').strftime('%H:%M') == '23:30'


@pytest.mark.skipif(not MODEL_PATH.exists(), reason='Train local artifact for integration tests')
def test_real_location_comparison_and_missing_data_contract():
    client = TestClient(app)
    result = client.post('/comparison', json={'latitude': 28.73, 'longitude': 77.12})
    assert result.status_code == 200, result.text
    data = result.json()
    assert data['year'] == 2025 and data['is_live'] is False
    assert len(data['phases']) == 3
    for phase in data['phases']:
        for name, coverage in [('recorded', 'observed_hours'), ('estimated', 'predicted_hours')]:
            reading = phase[name]
            if reading['pm25'] is not None:
                assert phase[coverage] >= 16
                assert abs(reading['cigarettes']['week'] - reading['pm25'] / 22 * 7) < 0.1
            else:
                assert reading['aqi'] is None and reading['cigarettes'] is None
    assert client.post('/comparison', json={'latitude': 30.3, 'longitude': 76.4}).status_code == 404
    assert client.post('/comparison', json={'latitude': 100, 'longitude': 77}).status_code == 422
    assert client.get('/locations').status_code == 200


@pytest.mark.skipif(not MODEL_PATH.exists(), reason='Train local artifact for integration tests')
def test_comparison_with_no_hours_returns_missing_values(monkeypatch):
    from src.actions import comparison
    empty = comparison.source_hours().iloc[:0]
    monkeypatch.setattr(comparison, 'source_hours', lambda: empty)
    comparison.station_comparison.cache_clear()
    try:
        phases = comparison.station_comparison('site_1430', str(MODEL_PATH))
        assert all(phase['recorded']['pm25'] is None and phase['estimated']['pm25'] is None for phase in phases)
    finally:
        comparison.station_comparison.cache_clear()
