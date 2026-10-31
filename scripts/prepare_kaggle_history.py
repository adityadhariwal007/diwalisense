"""Extract Delhi station-hour concentrations, preserving source timestamps and IDs."""
import hashlib
import json
from pathlib import Path
import zipfile
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
archive = ROOT/'data/raw/kaggle/air-quality-data-in-india.zip'
out = ROOT/'data/processed/kaggle_history'
out.mkdir(parents=True,exist_ok=True)
with zipfile.ZipFile(archive) as z:
    stations = pd.read_csv(z.open('stations.csv'))
    stations = stations[stations.City.eq('Delhi')].copy()
    stations.to_csv(out/'stations.csv',index=False)
    parts = []
    for chunk in pd.read_csv(z.open('station_hour.csv'),chunksize=200000,low_memory=False):
        subset = chunk[chunk.StationId.isin(stations.StationId)].copy()
        if not subset.empty:
            parts.append(subset)
d = pd.concat(parts,ignore_index=True)
d = d.rename(columns={'StationId':'source_station_id','Datetime':'source_time','PM2.5':'pm25'})
d['source_time'] = pd.to_datetime(d.source_time,errors='coerce')
d = d[d.source_time.dt.year.between(2017,2020)].copy()
d['pm25'] = pd.to_numeric(d.pm25,errors='coerce')
negative = int((d.pm25<0).sum())
d.loc[d.pm25<0,'pm25'] = float('nan')
d['timestamp_status'] = 'source_naive_timestamp_timezone_unverified'
d['station_id'] = 'kaggle_' + d.source_station_id
d['split'] = 'historical_development_only'
duplicates = int(d.duplicated(['station_id','source_time']).sum())
if duplicates:
    raise ValueError(f'Review {duplicates} duplicate source station hours')
d.to_parquet(out/'delhi_2017_2020.parquet',index=False)
d.to_csv(out/'delhi_2017_2020.csv.gz',index=False,compression='gzip')
d.assign(year=d.source_time.dt.year).groupby(['station_id','year']).agg(rows=('source_time','size'),valid_pm25=('pm25','count')).to_csv(out/'coverage.csv')
report = {'source':'https://www.kaggle.com/datasets/rohanrao/air-quality-data-in-india',
          'archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),
          'rows':len(d),'valid_pm25':int(d.pm25.notna().sum()),'stations':d.station_id.nunique(),
          'start':str(d.source_time.min()),'end':str(d.source_time.max()),'negative_pm25_masked':negative,
          'duplicate_station_times':duplicates,
          'status':'historical staging; timezone and station crosswalk must be resolved before combining with training_package',
          'license':'CC0: Public Domain, verified in Kaggle API catalog cached as data/raw/kaggle/catalog.json'}
(out/'manifest.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
