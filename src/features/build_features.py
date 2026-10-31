"""One row per station and UTC hour; pm25 in ug/m3, wind in m/s, height in m."""
import pandas as pd


def build_features(frame):
    required = {"station_id", "time", "pm25", "wind_speed_10m", "boundary_layer_height"}
    if not required.issubset(frame.columns) or frame.empty:
        raise ValueError(f"Need nonempty data with columns: {sorted(required)}")
    frame = frame.copy()
    frame["time"] = pd.to_datetime(frame["time"], utc=True)
    if frame[["station_id", "time"]].isna().any().any():
        raise ValueError("Station and time cannot be missing")
    if frame.duplicated(["station_id", "time"]).any():
        raise ValueError("Resolve duplicate station-hours / multiple sensors first")
    if (frame["time"] != frame["time"].dt.floor("h")).any():
        raise ValueError("Expected UTC hour-aligned timestamps")
    parts = []
    for station, group in frame.groupby("station_id"):
        group = group.set_index("time").sort_index().asfreq("h")
        group["station_id"] = station
        for column in ["pm25", "wind_speed_10m", "boundary_layer_height"]:
            group[column] = group[column].mask(group[column] < 0)
        group["ventilation_index"] = group["wind_speed_10m"] * group["boundary_layer_height"]
        group["pm25_lag_1h"] = group["pm25"].shift(1)
        group["pm25_lag_24h"] = group["pm25"].shift(24)
        group["pm25_prior_24h_mean"] = group["pm25"].shift(1).rolling(24, min_periods=24).mean()
        parts.append(group.reset_index())
    # TODO: sensor fault rules, issue-time joins, event-anchored accumulation, spatial features.
    return pd.concat(parts, ignore_index=True)
