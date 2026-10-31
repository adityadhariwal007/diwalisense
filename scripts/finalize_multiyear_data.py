"""Build separately attributed 2025 holdout; validate and package data for handoff."""
from pathlib import Path
import hashlib
import json
import shutil
import sys
import zipfile
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.features.build_features import build_features
OUT = ROOT/'data/processed/multiyear_training'
stations = pd.read_csv(OUT/'stations.csv')
weather = pd.read_parquet(OUT/'era5_weather_grids.parquet')
h = pd.read_parquet(ROOT/'data/processed/opencity/delhi_pm25_hourly.parquet')
h = h[h.time.dt.year.eq(2025)].copy()
h['source_time_ist'] = h.time.dt.tz_localize(None)
h['observation_time_utc'] = h.source_time_ist.dt.tz_localize('Asia/Kolkata').dt.tz_convert('UTC')
h['time'] = h.observation_time_utc.dt.floor('h')
h['available_no_earlier_than'] = h.time+pd.Timedelta(hours=1)
h['label_source'] = 'OpenCity_CPCB'
h['label_semantics'] = 'source_clock_hour_mean_minimum_3_quarterhour_records_IST_interpretation_provisional'
h['pm25_unit'] = 'ug/m3'
h['event_year'] = 2025
h['split'] = 'holdout_2025'
h['hours_from_diwali_midnight_local'] = (h.source_time_ist-pd.Timestamp('2025-10-20')).dt.total_seconds()/3600
h['is_event_inventory_window'] = h.hours_from_diwali_midnight_local.between(-336,192,inclusive='left')
h['is_candidate_burst_window'] = h.hours_from_diwali_midnight_local.between(-24,72,inclusive='left')
h = h.merge(stations[['station_id','weather_grid_id']],on='station_id',validate='many_to_one')
h = h.merge(weather,on=['weather_grid_id','time'],how='left',validate='many_to_one')
h['weather_type'] = 'ERA5_retrospective_UTC_bin_start_25km_grid'
h['timestamp_status'] = 'IST_inferred_from_2024_cross_source_agreement_not_confirmed_for_2025'
h.to_parquet(OUT/'opencity_holdout_2025.parquet',index=False)
h[h.is_event_inventory_window].to_parquet(OUT/'holdout_diwali_observations_2025.parquet',index=False)

validation = {'development':[]}
all_keys = set()
for year in range(2017,2025):
    d = pd.read_parquet(OUT/f'station_observations_{year}.parquet')
    assert (d.source_time_ist.dt.year==year).all()
    assert (d.observation_time_utc==d.time+pd.Timedelta(minutes=30)).all()
    assert not d.duplicated(['station_id','time']).any()
    assert d[['temperature_2m','relative_humidity_2m','wind_speed_10m']].notna().all().all()
    assert (d.pm25>=0).all() and d.relative_humidity_2m.between(0,100).all()
    assert (d.wind_speed_10m>=0).all() and (d.boundary_layer_height.dropna()>=0).all()
    keys = set(zip(d.station_id,d.time))
    assert all_keys.isdisjoint(keys)
    all_keys.update(keys)
    # Exercise the production feature-builder on observed hours including gaps.
    sample = d[d.station_id.eq(d.station_id.iloc[0])].sort_values('time').head(72)
    f = build_features(sample[['station_id','time','pm25','wind_speed_10m','boundary_layer_height']])
    assert f.time.diff().dropna().eq(pd.Timedelta(hours=1)).all()
    assert f.pm25_lag_1h.iloc[1:].reset_index(drop=True).equals(f.pm25.iloc[:-1].reset_index(drop=True))
    validation['development'].append({'year':year,'rows':len(d),'station_hours_unique':True,'feature_interface_passed':True})
assert not h.duplicated(['station_id','time']).any()
assert all_keys.isdisjoint(set(zip(h.station_id,h.time)))
assert h.temperature_2m.notna().all() and h.wind_speed_10m.notna().all()
assert h.loc[h.sample_count<3,'pm25'].isna().all()
e = h[h.is_event_inventory_window]
validation['holdout'] = {'rows':len(h),'valid_pm25':int(h.pm25.notna().sum()),'event_rows':len(e),
                         'event_valid_pm25':int(e.pm25.notna().sum()),'stations':h.station_id.nunique(),
                         'timestamp_interpretation':'provisional; no model tuning on this data'}
# Broader cross-source check: compare clocks, rather than incorrectly treating suffixes as true UTC.
a = pd.read_parquet(ROOT/'data/processed/opencity/delhi_pm25_hourly.parquet')
b = pd.read_parquet(ROOT/'data/raw/xkdr_history/delhi_pm25_2024.parquet')
b['time'] = pd.to_datetime(b.collected_at,utc=True)
m = a.merge(b,on=['station_id','time']).dropna(subset=['pm25','value'])
validation['cross_source_2024'] = {'pairs':len(m),'within_0_01_ug_m3':int(((m.pm25-m.value).abs()<0.01).sum()),
                                  'mae':float((m.pm25-m.value).abs().mean()),
                                  'scope':'Supports IST interpretation for 2024. Does not certify 2025 timestamps.'}
assert validation['cross_source_2024']['pairs']>300000
assert validation['cross_source_2024']['within_0_01_ug_m3']==len(m)
shutil.copyfile(ROOT/'data/processed/opencity/manifest.json',OUT/'opencity_source_manifest.json')
shutil.copyfile(ROOT/'data/processed/xkdr_history/download_manifest.json',OUT/'xkdr_source_manifest.json')
(OUT/'validation.json').write_text(json.dumps(validation,indent=2))
hashes = {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in OUT.iterdir() if p.is_file() and p.name!='sha256.json'}
(OUT/'sha256.json').write_text(json.dumps(hashes,indent=2))
dest = ROOT/'artifacts/diwalisense_multiyear_training.zip'
with zipfile.ZipFile(dest,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=3) as z:
    for p in OUT.iterdir():
        if p.is_file(): z.write(p,arcname=f'multiyear_training/{p.name}')
print(json.dumps(validation,indent=2))
print('Package',dest,'bytes',dest.stat().st_size)
