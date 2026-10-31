"""Validate delivered data invariants and compatibility, then create shareable ZIP."""
from pathlib import Path
import json
import shutil
import sys
import zipfile
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.features.build_features import build_features

out = ROOT/'data/processed/training_package'
summary = {}
keys = []
for split,year in [('development_2024',2024),('holdout_2025',2025)]:
    d = pd.read_parquet(out/f'{split}.parquet')
    assert d.station_id.nunique() == 39
    assert not d.duplicated(['station_id','time']).any()
    assert (d.time == d.time.dt.floor('h')).all()
    assert (d.time.dt.tz_convert('Asia/Kolkata').dt.year == year).all()
    assert ((d.time+pd.Timedelta(minutes=59)).dt.tz_convert('Asia/Kolkata').dt.year == year).all()
    assert not (d.pm25 < 0).any()
    assert d.loc[d.sample_count<3,'pm25'].isna().all()
    assert d.temperature_2m.notna().all() and d.wind_speed_10m.notna().all()
    assert d.relative_humidity_2m.dropna().between(0,100).all()
    assert (d.boundary_layer_height.dropna() >= 0).all()
    columns = ['station_id','time','pm25','wind_speed_10m','boundary_layer_height']
    # Exercise the real repository interface on a contiguous station slice.
    sample = d[d.station_id.eq(d.station_id.iloc[0])].head(72)[columns]
    f = build_features(sample)
    assert len(f) == len(sample)
    assert f.pm25_lag_1h.iloc[1:].reset_index(drop=True).equals(sample.pm25.iloc[:-1].reset_index(drop=True))
    keys.append(set(zip(d.station_id,d.time)))
    summary[split] = {'rows':len(d),'valid_pm25':int(d.pm25.notna().sum()),
                      'complete_required_rows':int(d[columns].notna().all(axis=1).sum())}
assert keys[0].isdisjoint(keys[1])
summary['checks'] = 'Passed: unique/aligned UTC hours, disjoint local-year splits including bin ends, PM2.5 completeness and nonnegative values, weather ranges, repository feature builder and lag behavior.'
(out/'validation.json').write_text(json.dumps(summary,indent=2))
shutil.copyfile(ROOT/'docs/TRAINING_DATA_HANDOFF.md',out/'README.md')
dest = ROOT/'artifacts/diwalisense_training_data.zip'
dest.parent.mkdir(exist_ok=True)
with zipfile.ZipFile(dest,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=3) as z:
    for folder in [out,ROOT/'data/processed/kaggle_history']:
        for p in folder.iterdir():
            if p.is_file():
                z.write(p,arcname=f'{folder.name}/{p.name}')
    z.write(ROOT/'data/processed/opencity/manifest.json',arcname='provenance/opencity_manifest.json')
    z.write(ROOT/'data/raw/kaggle/catalog.json',arcname='provenance/kaggle_catalog.json')
print(json.dumps(summary,indent=2))
print('ZIP',dest,'bytes',dest.stat().st_size)
