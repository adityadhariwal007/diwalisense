"""Prepare versioned source-aware training inputs and event inventories, not residual targets."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import time
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT/'data/raw/xkdr_history'
OUT = ROOT/'data/processed/multiyear_training'
OUT.mkdir(parents=True,exist_ok=True)
DATES = {
2017:('2017-10-19','https://www.nadt.gov.in/writereaddata/MenuContentImages/Administrative%20Handbook%202017636487657655593645.pdf'),
2018:('2018-11-07','https://surveyofindia.gov.in/files/Holiday%20List%202018.pdf'),
2019:('2019-10-27','https://vicepresidentofindia.nic.in/sites/default/files/holidays19.pdf'),
2020:('2020-11-14','https://saiindia.gov.in/uploads/media/Holiday-List-2020-20200625160616.pdf'),
2021:('2021-11-04','https://saiindia.gov.in/uploads/media/Holiday-List-DGA-F-C-2021-20210927115302.pdf'),
2022:('2022-10-24','https://saiindia.gov.in/uploads/media/Lists-of-Compulsory-Restricted-Holidays-to-be-observed-by-this-Office-during-the-calendar-year-2022-2-20211213125642.pdf'),
2023:('2023-11-12','https://www.lpsc.gov.in/holidaysBangalore2023.html'),
2024:('2024-10-31','https://cgca.gov.in/ccatn/list-of-holiday'),
2025:('2025-10-20','https://www.sci.gov.in/holiday-description/2025/'),
}
pd.DataFrame([{'year':y,'diwali_date_local':v[0],'source_url':v[1],'timezone':'Asia/Kolkata',
               'anchor':'local_calendar_midnight_not_measured_emission_start'} for y,v in DATES.items()]).to_csv(OUT/'event_calendar.csv',index=False)
stations = pd.read_csv(ROOT/'data/raw/xkdr_stations.csv')
stations['weather_latitude'] = (stations.latitude*4).round()/4
stations['weather_longitude'] = (stations.longitude*4).round()/4
stations['weather_grid_id'] = stations.apply(lambda r:f'{r.weather_latitude:.2f}_{r.weather_longitude:.2f}',axis=1)
stations.to_csv(OUT/'stations.csv',index=False)

def fetch_weather(task):
    lat,lon,gid,year = task
    p = ROOT/'data/raw/era5_multiyear'/f'{gid}_{year}.json'
    if not p.exists():
        p.parent.mkdir(parents=True,exist_ok=True)
        for attempt in range(3):
            try:
                r = requests.get('https://archive-api.open-meteo.com/v1/archive',params={
                    'latitude':lat,'longitude':lon,'start_date':f'{year}-01-01','end_date':f'{year}-12-31',
                    'hourly':'temperature_2m,relative_humidity_2m,wind_speed_10m,boundary_layer_height',
                    'models':'era5','wind_speed_unit':'ms','timezone':'UTC'},timeout=120)
                r.raise_for_status()
                payload = r.json()
                assert 'hourly' in payload
                p.write_bytes(r.content)
                break
            except Exception:
                if attempt==2: raise
                time.sleep(4*(attempt+1))
    payload = json.loads(p.read_text())
    w = pd.DataFrame(payload['hourly'])
    w['time'] = pd.to_datetime(w.time,utc=True)
    w['weather_grid_id'] = gid
    w['weather_grid_latitude'] = payload['latitude']
    w['weather_grid_longitude'] = payload['longitude']
    print('Weather',gid,year,flush=True)
    return w

grids = stations[['weather_latitude','weather_longitude','weather_grid_id']].drop_duplicates()
tasks = [(lat,lon,gid,y) for lat,lon,gid in grids.itertuples(index=False,name=None) for y in range(2016,2026)]
with ThreadPoolExecutor(max_workers=2) as pool:
    weather = pd.concat(pool.map(fetch_weather,tasks),ignore_index=True)
assert not weather.duplicated(['weather_grid_id','time']).any()
weather.to_parquet(OUT/'era5_weather_grids.parquet',index=False)
year_reports = []
event_frames = []
for year in range(2017,2026):
    d = pd.read_parquet(RAW/f'delhi_pm25_{year}.parquet')
    assert set(d.parameter_name)=={'PM2.5'}
    assert not d.duplicated(['station_id','collected_at']).any()
    d['source_time_ist'] = pd.to_datetime(d.collected_at)
    d['observation_time_utc'] = d.source_time_ist.dt.tz_localize('Asia/Kolkata').dt.tz_convert('UTC')
    # A UTC bin identifies the record, not a claim about its original integration period.
    d['time'] = d.observation_time_utc.dt.floor('h')
    d['pm25'] = pd.to_numeric(d.value,errors='coerce').mask(lambda s:s<0)
    d['pm25_unit'] = 'ug/m3'
    d['source_unit_original'] = d.unit
    d['label_source'] = 'XKDR_CPCB'
    d['label_semantics'] = 'published_record_in_UTC_bin_original_averaging_interval_unverified'
    d['available_no_earlier_than'] = d.time+pd.Timedelta(hours=1)
    d['split'] = 'development' if year<=2024 else 'holdout_partial_no_diwali'
    d['event_year'] = year
    anchor = pd.Timestamp(DATES[year][0])
    d['hours_from_diwali_midnight_local'] = (d.source_time_ist-anchor).dt.total_seconds()/3600
    d['is_event_inventory_window'] = d.hours_from_diwali_midnight_local.between(-14*24,8*24,inclusive='left')
    d['is_candidate_burst_window'] = d.hours_from_diwali_midnight_local.between(-24,72,inclusive='left')
    d = d.merge(stations[['station_id','weather_grid_id']],on='station_id',how='left',validate='many_to_one')
    assert d.weather_grid_id.notna().all()
    d = d.merge(weather,on=['weather_grid_id','time'],how='left',validate='many_to_one')
    d['weather_type'] = 'ERA5_retrospective_UTC_bin_start_25km_grid'
    assert not d.duplicated(['station_id','time']).any()
    d = d.drop(columns=['collected_at','value','unit','parameter_name'])
    d.to_parquet(OUT/f'station_observations_{year}.parquet',index=False)
    event = d[d.is_event_inventory_window].copy()
    event_frames.append(event)
    cov = event.groupby('station_id').agg(records=('time','size'),valid_pm25=('pm25','count'),valid_blh=('boundary_layer_height','count'))
    cov['event_year'] = year
    cov.to_csv(OUT/f'event_coverage_{year}.csv')
    year_reports.append({'year':year,'rows':len(d),'valid_pm25':int(d.pm25.notna().sum()),
        'complete_required_rows':int(d[['pm25','wind_speed_10m','boundary_layer_height']].notna().all(axis=1).sum()),
        'stations':d.station_id.nunique(),'first_local':str(d.source_time_ist.min()),'last_local':str(d.source_time_ist.max()),
        'event_rows':len(event),'event_valid_pm25':int(event.pm25.notna().sum()),
        'stations_with_75pct_event_pm25':int((cov.valid_pm25>=396).sum())})
    print('Prepared',year,year_reports[-1],flush=True)
events = pd.concat(event_frames,ignore_index=True)
events[events.event_year<=2024].to_parquet(OUT/'development_diwali_observations_2017_2024.parquet',index=False)
report = {'source':'https://airquality.xkdr.org/','attribution':'XKDR Forum; CPCB CAAQM, CC BY 4.0. Weather: Open-Meteo / Copernicus ERA5, CC BY 4.0.',
          'status':'retrospective_observation_inputs_not_fitted_models_or_residual_targets',
          'years':year_reports,'event_inventory_window':'14 days before through 7 days after, local midnight anchor',
          'candidate_burst_window':'1 day before through 2 days after; design parameter requiring sensitivity checks',
          'limitations':['2025 XKDR Delhi observations do not cover Diwali; use separately attributed OpenCity holdout.',
            'UTC time is a record bin; observation_time_utc preserves actual +30 minute timing. Source averaging interval and publication latency are unknown.',
            'Weather sampled at bin start, up to 30 minutes before observation timestamp; ERA5 grid weather is not issued forecasts.',
            'Missing hours/labels are not imputed; feature builder must reindex each station before lagging.',
            'Event inventory contains no residual label: model teammate must supply strictly out-of-time baseline predictions.',
            'No verified fire, restriction-policy or ward features are included. Station records are not independent festivals.']}
(OUT/'quality_report.json').write_text(json.dumps(report,indent=2))
hashes = {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in OUT.iterdir() if p.is_file() and p.name!='sha256.json'}
(OUT/'sha256.json').write_text(json.dumps(hashes,indent=2))
