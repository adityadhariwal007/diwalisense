"""Build an auditable retrospective starter dataset without changing model code.

OpenCity UTC suffixes are interpreted as IST wall-clock only after cross-source
checks. Raw files and the original provisional aggregate remain unchanged.
"""
from pathlib import Path
import hashlib
import json
import time
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'data/raw'
OUT = ROOT / 'data/processed/training_package'
OUT.mkdir(parents=True, exist_ok=True)
HEADERS = {'Authorization': 'Bearer aqi_demo_wbf92Qx21zX-Wa_Tg8Dx1nXe'}  # Published public demo key.

def get(url, path, **kwargs):
    if path.exists():
        return path.read_bytes()
    for attempt in range(3):
        try:
            r = requests.get(url, timeout=120, **kwargs)
            r.raise_for_status()
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(r.content)
            return r.content
        except requests.RequestException:
            if attempt == 2:
                raise
            time.sleep(3 * (attempt + 1))

def main():
    manifest = json.loads((RAW/'../processed/opencity/manifest.json').resolve().read_text())
    (OUT/'source_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    stations = pd.read_csv(RAW/'xkdr_stations.csv')
    ids = set(pd.read_parquet(ROOT/'data/processed/opencity/delhi_pm25_hourly.parquet',columns=['station_id']).station_id)
    stations = stations[stations.station_id.isin(ids)].copy()
    assert len(stations) == len(ids) and stations.station_id.is_unique
    assert stations[['latitude','longitude']].notna().all().all()
    stations.to_csv(OUT/'stations.csv', index=False)
    original = pd.read_parquet(ROOT/'data/processed/opencity/delhi_pm25_hourly.parquet')
    checks = []
    for station, date in [('site_5024','2024-01-01'),('site_301','2024-11-01'),('site_1560','2024-06-01')]:
        path = RAW/'timestamp_checks'/f'{station}_{date}.csv'
        get('https://airquality.xkdr.org/v1/measurements',path,headers=HEADERS,
            params={'station':station,'parameter':'PM2.5','start':date,'end':date,'format':'csv'})
        b = pd.read_csv(path)
        b['time'] = pd.to_datetime(b.collected_at,utc=True)
        a = original[original.station_id.eq(station)].merge(b,on=['station_id','time'])
        usable = a.dropna(subset=['pm25','value'])
        exact = int(((usable.pm25-usable.value).abs()<1e-6).sum())
        checks.append({'station_id':station,'date':date,'compared':len(usable),'exact_matches':exact,
                       'mean_absolute_difference':float((usable.pm25-usable.value).abs().mean())})
    (OUT/'timestamp_audit.json').write_text(json.dumps(checks,indent=2))
    if any(c['compared']<12 or c['exact_matches']/c['compared']<0.9 for c in checks):
        raise ValueError('Timestamp hypothesis requires manual review; refusing weather merge')

    frames = []
    for r in manifest['resources']:
        if r['status'] != 'ok':
            continue
        d = pd.read_csv(RAW/'opencity'/f"{r['resource_id']}.csv")
        # Ignore the incorrect +0000 suffix, localize the displayed clock to IST,
        # then aggregate the ORIGINAL quarter-hour samples into UTC clock hours.
        t = pd.to_datetime(d.Timestamp,utc=True,errors='coerce').dt.tz_localize(None).dt.tz_localize('Asia/Kolkata').dt.tz_convert('UTC')
        value = pd.to_numeric(d[next(c for c in d if c.startswith('PM2.5 ('))],errors='coerce')
        clean = pd.DataFrame({'time':t,'station_id':d['Station ID'],'pm25':value.mask(value<0)})
        clean = clean.dropna(subset=['time'])
        assert not clean.duplicated(['station_id','time']).any()
        for station, g in clean.groupby('station_id'):
            h = g.set_index('time').pm25.resample('h').agg(['mean','count'])
            h.columns = ['pm25','sample_count']
            h.loc[h.sample_count<3,'pm25'] = float('nan')
            h['station_id'] = station
            h['source_resource_id'] = r['resource_id']
            frames.append(h.reset_index())
    air = pd.concat(frames,ignore_index=True)
    # Partial edge hours are kept with missing labels, not invented or padded.
    air['local_year'] = air.time.dt.tz_convert('Asia/Kolkata').dt.year
    air['split'] = air.local_year.map({2024:'development_2024',2025:'holdout_2025'})
    end_year = (air.time + pd.Timedelta(minutes=59)).dt.tz_convert('Asia/Kolkata').dt.year
    air.loc[air.local_year.ne(end_year), 'split'] = 'year_boundary_excluded'
    air['timestamp_status'] = 'IST_interpretation_cross_source_supported'
    air['available_no_earlier_than'] = air.time + pd.Timedelta(hours=1)
    air.to_parquet(OUT/'pm25_hourly.parquet',index=False)
    print('PM25 prepared',len(air),flush=True)

    def weather(row):
        sid = row.station_id
        p = RAW/'openmeteo_training'/f'{sid}_2023-12-31_2025-12-31.json'
        payload = json.loads(get('https://archive-api.open-meteo.com/v1/archive',p,params={
            'latitude':row.latitude,'longitude':row.longitude,'start_date':'2023-12-31','end_date':'2025-12-31',
            'hourly':'temperature_2m,relative_humidity_2m,wind_speed_10m,boundary_layer_height',
            'wind_speed_unit':'ms','timezone':'UTC'}))
        w = pd.DataFrame(payload['hourly'])
        w['time'] = pd.to_datetime(w.time,utc=True)
        w['station_id'] = sid
        w['weather_grid_latitude'] = payload['latitude']
        w['weather_grid_longitude'] = payload['longitude']
        print('Weather',sid,len(w),flush=True)
        return w
    with ThreadPoolExecutor(max_workers=2) as pool:
        weather_data = pd.concat(pool.map(weather,stations.itertuples(index=False)),ignore_index=True)
    weather_data.to_parquet(OUT/'weather_hourly.parquet',index=False)
    joined = air.merge(weather_data,on=['station_id','time'],how='left',validate='one_to_one')
    joined['weather_type'] = 'historical_reanalysis_not_issued_forecast'
    assert not joined.duplicated(['station_id','time']).any()
    assert (joined.time == joined.time.dt.floor('h')).all()
    required = ['pm25','wind_speed_10m','boundary_layer_height']
    for split, frame in joined.groupby('split'):
        frame.to_parquet(OUT/f'{split}.parquet',index=False)
        frame.to_csv(OUT/f'{split}.csv.gz',index=False,compression='gzip')
    coverage = joined.groupby(['station_id','split']).agg(hours=('time','size'),valid_pm25=('pm25','count'),valid_wind=('wind_speed_10m','count'),valid_blh=('boundary_layer_height','count'))
    coverage.to_csv(OUT/'coverage.csv')
    report = {'rows':len(joined),'stations':joined.station_id.nunique(),'valid_pm25':int(joined.pm25.notna().sum()),
              'complete_required_rows':int(joined[required].notna().all(axis=1).sum()),
              'timestamp_policy':'IST wall-clock interpretation supported by 3 sampled 2024 station-days from XKDR; not provider-confirmed for all stations/2025. UTC-hour bins use original quarter-hour observations. Bins spanning local year boundaries are excluded from development/holdout.',
              'limitations':['Only 2024-2025 Delhi; 2017-2023 and NCR outside Delhi are not covered.',
                'Repeated quarter-hour readings may not be independent measurements.',
                'Reanalysis weather supports retrospective experiments, not operational forecast validation.',
                'Reporting latency is unknown; available_no_earlier_than is only the end of the aggregation interval.'],
              'files':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in OUT.iterdir() if p.is_file() and p.name!='quality_report.json'}}
    (OUT/'quality_report.json').write_text(json.dumps(report,indent=2))
    print(json.dumps({k:v for k,v in report.items() if k!='files'}),flush=True)

if __name__ == '__main__':
    main()
