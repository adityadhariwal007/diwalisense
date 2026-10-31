"""Six-hour-ahead features from prior bins; no target-time observations."""
import numpy as np
import pandas as pd

HORIZON = 6
FEATURES = ['pm25_lag6', 'pm25_lag24', 'pm25_lag48', 'pm25_prior24_mean',
            'wind_prior', 'blh_prior', 'ventilation_prior', 'temperature_prior',
            'humidity_prior', 'hour_sin', 'hour_cos', 'season_sin', 'season_cos',
            'latitude', 'longitude']
BURST_FEATURES = FEATURES + ['hours_from_diwali']
DIWALI = {2024: '2024-10-31', 2025: '2025-10-20'}


def hourly_features(frame, stations):
    required = {'time', 'station_id', 'pm25', 'available_no_earlier_than',
                'wind_speed_10m', 'boundary_layer_height', 'temperature_2m', 'relative_humidity_2m'}
    if not required.issubset(frame):
        raise ValueError('Missing required timestamp, pollutant or weather fields')
    frame = frame.copy()
    frame['time'] = pd.to_datetime(frame.time, utc=True)
    frame['available_no_earlier_than'] = pd.to_datetime(frame.available_no_earlier_than, utc=True)
    if frame.duplicated(['station_id', 'time']).any():
        raise ValueError('Duplicate station-hours')
    if frame.time.isna().any() or (frame.time != frame.time.dt.floor('h')).any():
        raise ValueError('Expected aligned UTC hours')
    parts = []
    for station, group in frame.groupby('station_id'):
        group = group.set_index('time').sort_index().asfreq('h')
        group['station_id'] = station
        group['pm25'] = group.pm25.mask(group.pm25 < 0)
        # A source bin at t-7 ends at t-6: six full hours before target-bin start.
        for lag in [6, 24, 48]:
            group[f'pm25_lag{lag}'] = group.pm25.shift(lag + 1)
        group['pm25_prior24_mean'] = group.pm25.shift(HORIZON + 1).rolling(24, min_periods=18).mean()
        for name, source in [('wind', 'wind_speed_10m'), ('blh', 'boundary_layer_height'),
                             ('temperature', 'temperature_2m'), ('humidity', 'relative_humidity_2m')]:
            group[f'{name}_prior'] = group[source].shift(HORIZON + 1)
        group['ventilation_prior'] = group.wind_prior * group.blh_prior
        group['input_available_at'] = group.available_no_earlier_than.shift(HORIZON + 1)
        parts.append(group.reset_index())
    result = pd.concat(parts, ignore_index=True)
    result['issue_time'] = result.time - pd.Timedelta(hours=HORIZON)
    if (result.input_available_at.dropna() > result.loc[result.input_available_at.notna(), 'issue_time']).any():
        raise ValueError('Input availability exceeds forecast issue time')
    local = result.time.dt.tz_convert('Asia/Kolkata')
    event_dates = local.dt.year.map(DIWALI)
    if event_dates.isna().any():
        raise ValueError('Missing verified event calendar year')
    anchor = pd.to_datetime(event_dates).dt.tz_localize('Asia/Kolkata') + pd.Timedelta(hours=18)
    result['hours_from_diwali'] = (local - anchor).dt.total_seconds() / 3600
    result['event'] = result.hours_from_diwali.between(-24, 48)
    result['hour_sin'] = np.sin(2 * np.pi * (local.dt.hour + 0.5) / 24)
    result['hour_cos'] = np.cos(2 * np.pi * (local.dt.hour + 0.5) / 24)
    result['season_sin'] = np.sin(2 * np.pi * local.dt.dayofyear / 365.25)
    result['season_cos'] = np.cos(2 * np.pi * local.dt.dayofyear / 365.25)
    result = result.merge(stations[['station_id', 'latitude', 'longitude']], on='station_id', how='left', validate='many_to_one')
    # Fixed six-hour schedule limits demo size; never fill missing targets or persistence inputs.
    return result[(result.time.dt.hour % 6 == 0)].dropna(subset=['pm25', 'pm25_lag6', 'input_available_at']).reset_index(drop=True)
