"""Cache Delhi CPCB PM2.5 history using a private key, preserving native timestamps."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import hashlib
import io
import json
import os
import time
import pandas as pd
import requests
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT/'data/raw/xkdr_history'
OUT = ROOT/'data/processed/xkdr_history'
RAW.mkdir(parents=True,exist_ok=True)
OUT.mkdir(parents=True,exist_ok=True)
key = dotenv_values(ROOT/'.env').get('XKDR_API_KEY') or os.getenv('XKDR_API_KEY')
if not key:
    raise SystemExit('Set XKDR_API_KEY in .env')
headers = {'Authorization':f'Bearer {key}'}
base = 'https://airquality.xkdr.org/v1/'
for endpoint in ['meta','stations']:
    r = requests.get(base+endpoint,headers=headers,params={'city':'Delhi'} if endpoint=='stations' else {},timeout=90)
    r.raise_for_status()
    (RAW/f'{endpoint}.json').write_bytes(r.content)

def collect(year):
    path = RAW/f'delhi_pm25_{year}.parquet'
    if not path.exists():
        for attempt in range(3):
            try:
                r = requests.get(base+'measurements',headers=headers,params={
                    'city':'Delhi','source':'cpcb_caaqm','parameter':'PM2.5',
                    'start':f'{year}-01-01','end':f'{year}-12-31','format':'parquet'},timeout=120)
                r.raise_for_status()
                pd.read_parquet(io.BytesIO(r.content))  # Validate before caching.
                path.write_bytes(r.content)
                break
            except Exception:
                if attempt==2:
                    raise RuntimeError(f'History request failed for {year}; no credentials printed') from None
                time.sleep(3*(attempt+1))
    d = pd.read_parquet(path)
    print(year,len(d),list(d.columns),flush=True)
    return {'year':year,'rows':len(d),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}

with ThreadPoolExecutor(max_workers=2) as pool:
    records = list(pool.map(collect,range(2017,2026)))
(OUT/'download_manifest.json').write_text(json.dumps({'source':'https://airquality.xkdr.org/',
    'attribution':'India Air Quality Database, XKDR Forum; CPCB CAAQM. CC BY 4.0.',
    'files':records},indent=2))
