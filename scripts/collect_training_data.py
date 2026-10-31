"""Download documented OpenCity concentration archives; preserve raw data and audit hourly output."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import hashlib,json,time
import pandas as pd
import requests

ROOT=Path(__file__).resolve().parents[1]
RAW=ROOT/'data/raw/opencity'
OUT=ROOT/'data/processed/opencity'
RAW.mkdir(parents=True,exist_ok=True); OUT.mkdir(parents=True,exist_ok=True)
catalog_path=ROOT/'data/raw/opencity_catalog.json'
if not catalog_path.exists():
    response=requests.get('https://data.opencity.in/api/3/action/package_show',params={'id':'delhi-hourly-air-quality-reports'},timeout=60)
    response.raise_for_status()
    catalog_path.write_text(json.dumps(response.json()['result'],indent=2),encoding='utf-8')
catalog=json.loads(catalog_path.read_text(encoding='utf-8'))
resources=[r for r in catalog['resources'] if '2024-25' in r['name']]

def process(r):
    p=RAW/(r['id']+'.csv')
    result={'resource_id':r['id'],'name':r['name'],'url':r['url']}
    try:
        existing=ROOT/'data/raw'/(r['id']+'.csv')
        if not p.exists():
            if existing.exists(): p.write_bytes(existing.read_bytes())
            else:
                for attempt in range(3):
                    try:
                        resp=requests.get(r['url'],timeout=120);resp.raise_for_status()
                        if 'Station ID' not in resp.text[:500]: raise ValueError('Unexpected schema')
                        p.write_bytes(resp.content);break
                    except Exception:
                        if attempt==2: raise
                        time.sleep(2*(attempt+1))
        result['sha256']=hashlib.sha256(p.read_bytes()).hexdigest()
        df=pd.read_csv(p)
        key=next(c for c in df if c.startswith('PM2.5 ('))
        t=pd.to_datetime(df['Timestamp'],utc=True,errors='coerce')
        v=pd.to_numeric(df[key],errors='coerce')
        result.update(raw_rows=len(df),invalid_timestamps=int(t.isna().sum()),negative_pm25=int((v<0).sum()))
        clean=pd.DataFrame({'station_id':df['Station ID'].astype(str),'time':t,'pm25':v.mask(v<0)})
        result['duplicate_timestamps']=int(clean.duplicated(['station_id','time']).sum())
        clean=clean.dropna(subset=['time']).drop_duplicates(['station_id','time'],keep='first')
        groups=[]
        for station,g in clean.groupby('station_id'):
            h=g.set_index('time').resample('h')['pm25'].agg(['mean','count'])
            h=h.rename(columns={'mean':'pm25','count':'sample_count'})
            h.loc[h.sample_count<3,'pm25']=float('nan')
            h['station_id']=station;h['source_resource_id']=r['id']
            h['timestamp_status']='source_labels_UTC_not_independently_verified'
            h['split']=h.index.year.map(lambda y:'holdout_2025' if y==2025 else 'development')
            groups.append(h.reset_index())
        hourly=pd.concat(groups,ignore_index=True)
        hourly.to_parquet(OUT/(r['id']+'.parquet'),index=False)
        coverage=hourly.assign(year=hourly.time.dt.year).groupby(['station_id','year']).agg(hours=('time','size'),valid_pm25=('pm25','count')).reset_index()
        result.update(status='ok',hourly_rows=len(hourly),valid_pm25=int(hourly.pm25.notna().sum()),start=str(hourly.time.min()),end=str(hourly.time.max()),coverage=coverage.to_dict('records'),stations=df[['Station ID','Station Name','City','State']].drop_duplicates().to_dict('records'))
    except Exception as e: result.update(status='failed',error=str(e))
    print(json.dumps({k:result.get(k) for k in ['name','status','hourly_rows','valid_pm25','error']}),flush=True)
    return result

with ThreadPoolExecutor(max_workers=3) as pool: results=list(pool.map(process,resources))
(OUT/'manifest.json').write_text(json.dumps({'catalog_license':catalog.get('license_title'),'source':'https://data.opencity.in/dataset/delhi-hourly-air-quality-reports','resources':results},indent=2),encoding='utf-8')
coverage=[x for r in results for x in r.get('coverage',[])]
pd.DataFrame(coverage).to_csv(OUT/'coverage.csv',index=False)
frames=[pd.read_parquet(OUT/(r['resource_id']+'.parquet')) for r in results if r['status']=='ok']
if frames:
    combined=pd.concat(frames,ignore_index=True).sort_values(['station_id','time'])
    if combined.duplicated(['station_id','time']).any(): raise ValueError('Cross-resource duplicate station hours require review')
    combined.to_parquet(OUT/'delhi_pm25_hourly.parquet',index=False)
    combined.to_csv(OUT/'delhi_pm25_hourly.csv.gz',index=False,compression='gzip')
    print('TOTAL',len(combined),'VALID',combined.pm25.notna().sum(),flush=True)
