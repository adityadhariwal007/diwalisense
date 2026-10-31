"""Audit staged historical event coverage; does not declare data train-ready."""
from pathlib import Path
import json
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'data/processed/event_preparation'
OUT.mkdir(parents=True,exist_ok=True)
events = [
    {'year':2017,'date':'2017-10-19','source':'https://www.nadt.gov.in/writereaddata/MenuContentImages/Administrative%20Handbook%202017636487657655593645.pdf'},
    {'year':2018,'date':'2018-11-07','source':'https://surveyofindia.gov.in/files/Holiday%20List%202018.pdf'},
    {'year':2019,'date':'2019-10-27','source':'https://vicepresidentofindia.nic.in/sites/default/files/holidays19.pdf'},
]
d = pd.read_parquet(ROOT/'data/processed/kaggle_history/delhi_2017_2020.parquet')
for event in events:
    anchor = pd.Timestamp(event['date'])
    start,end = anchor-pd.Timedelta(days=14),anchor+pd.Timedelta(days=8)
    sample = d[(d.source_time>=start)&(d.source_time<end)]
    counts = sample.groupby('station_id').pm25.agg(['size','count'])
    event.update(window_start=str(start),window_end_exclusive=str(end),expected_hours_per_station=528,
                 total_records=len(sample),valid_pm25=int(sample.pm25.notna().sum()),
                 stations_with_75pct_valid=int((counts['count']>=396).sum()),
                 station_coverage=counts.reset_index().to_dict('records'))
report = {'status':'coverage_audit_only_not_train_ready',
          'timestamp_basis':'unverified source wall-clock; no UTC conversion claimed',
          'window_rationale':'22-day inventory window, not a causal attribution or final event exclusion definition',
          'remaining':['Verify timezone/interval semantics and station crosswalk',
                       'Join matching historical weather and document missing mixing height',
                       'Audit peak-hour coverage separately; 75% window coverage is only a screening threshold',
                       'Build residual targets using strictly earlier-time baseline training',
                       'Evaluate development events chronologically; reserve 2025 for final evaluation'],
          'events':events}
(OUT/'historical_diwali_coverage.json').write_text(json.dumps(report,indent=2))
print(json.dumps([{k:v for k,v in e.items() if k!='station_coverage'} for e in events],indent=2))
