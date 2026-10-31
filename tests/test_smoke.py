from unittest.mock import Mock, patch

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from api.main import app
from src.features.build_features import build_features
from src.ingestion.firms import fetch_fire_counts
from src.ingestion.open_meteo import fetch_weather
from src.ingestion.openaq import _pages, fetch_delhi_pm25


def test_features_do_not_bridge_gaps_or_stations():
    frame = pd.DataFrame({
        "station_id": [1, 1, 1, 2],
        "time": ["2025-01-01T00:00Z", "2025-01-01T01:00Z",
                 "2025-01-01T03:00Z", "2025-01-01T00:00Z"],
        "pm25": [10, 20, 30, 999], "wind_speed_10m": [2]*4,
        "boundary_layer_height": [100]*4,
    })
    result = build_features(frame)
    one = result[result.station_id == 1].reset_index(drop=True)
    assert one.loc[1, "pm25_lag_1h"] == 10
    assert pd.isna(one.loc[3, "pm25_lag_1h"])
    assert one.loc[0, "ventilation_index"] == 200
    assert pd.isna(result[result.station_id == 2].iloc[0].pm25_lag_1h)
    with pytest.raises(ValueError):
        build_features(pd.concat([frame, frame.iloc[:1]]))


def test_dummy_api():
    response = TestClient(app).get("/forecast", params={"ward": "Test"})
    assert response.status_code == 200
    assert response.json()["is_dummy"] is True
    assert response.json()["ward"] == "Test"


def test_weather_units_and_missing_height():
    payload = {"hourly": {"time": ["2025-01-01T00:00"],
               "temperature_2m": [10], "relative_humidity_2m": [50],
               "wind_speed_10m": [2], "boundary_layer_height": [100]}}
    with patch("src.ingestion.open_meteo.requests.get") as get:
        get.return_value.json.return_value = payload
        assert len(fetch_weather(28.6, 77.2, "2025-01-01", "2025-01-01")) == 1
        assert get.call_args.kwargs["params"]["wind_speed_unit"] == "ms"
        payload["hourly"]["boundary_layer_height"] = [None]
        with pytest.raises(ValueError):
            fetch_weather(28.6, 77.2, "2025-01-01", "2025-01-01")


def test_openaq_pagination():
    session = Mock()
    session.get.side_effect = [
        Mock(json=lambda: {"results": list(range(100))}),
        Mock(json=lambda: {"results": [100]}),
    ]
    assert len(list(_pages(session, "/locations", {}))) == 101
    assert session.get.call_args.kwargs["params"]["page"] == 2


def test_openaq_hourly_schema(monkeypatch):
    monkeypatch.setenv("OPENAQ_API_KEY", "test")
    station = {"id": 1, "sensors": [{"id": 9, "parameter": {"name": "pm25"}}]}
    row = {"value": 42, "parameter": {"units": "µg/m³"},
           "flagInfo": {"hasFlags": False}, "period": {
               "datetimeFrom": {"utc": "2025-01-01T00:00:00Z"},
               "datetimeTo": {"utc": "2025-01-01T01:00:00Z"}}}
    with patch("src.ingestion.openaq._pages", side_effect=[[station], [row]]):
        result = fetch_delhi_pm25("2025-01-01T00:00Z", "2025-01-02T00:00Z")
        assert result.iloc[0].pm25 == 42
        assert result.iloc[0].sensor_id == 9


def test_fire_counts_and_bad_response(monkeypatch):
    monkeypatch.setenv("FIRMS_MAP_KEY", "test")
    with patch("src.ingestion.firms.requests.get") as get:
        get.return_value.text = "acq_date,latitude\n2025-01-01,28\n2025-01-01,29\n"
        counts = fetch_fire_counts("2025-01-01", days=2)
        assert counts.fire_detections.tolist() == [2, 0]
        get.return_value.text = "Invalid MAP_KEY"
        with pytest.raises(ValueError):
            fetch_fire_counts("2025-01-01")


def test_quantile_skeletons():
    from src.models.baseline import train_baseline
    from src.models.burst import train_burst

    X = pd.DataFrame({"wind": range(60)})
    y = pd.Series([100.0 + i for i in range(60)])
    for models in (train_baseline(X, y), train_burst(X, y, y - 5)):
        assert set(models) == {0.1, 0.5, 0.9}
        assert len(models[0.5].predict(X.iloc[:2])) == 2
