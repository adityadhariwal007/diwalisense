# Multi-year training inputs

Use this package for new baseline and event experiments in preference to concatenating the old Kaggle staging files with the first 2024-only package. Do not concatenate versions: they contain overlapping CPCB measurements with different processing definitions.

## Contents and readiness

- `station_observations_2017.parquet` through `station_observations_2024.parquet`: 2,206,334 published PM2.5 observations across up to 39 Delhi stations, joined to historical weather. There are 2,047,701 records with PM2.5, wind and mixing height present. Missing station-hours are absent records, not zero pollution.
- `development_diwali_observations_2017_2024.parquet`: 134,525 event-inventory observations around eight annual Diwalis; all have the required weather. These are observations and known calendar features, **not residual training targets**. 2017 is particularly sparse and useful primarily as early training history.
- `opencity_holdout_2025.parquet`: 341,640 hourly records, 318,620 nonmissing PM2.5 labels. `holdout_diwali_observations_2025.parquet` contains 20,592 event-window rows, with 19,571 labels. This source uses a provisional IST interpretation supported by agreement in 2024, not independently verified in 2025. Holdout quantities are inventory/completeness checks, not forecast-performance results.
- `station_observations_2025.parquet`: separate XKDR partial-year observations, April–September only. They do not cover Diwali. Do not merge these into development or append them to the full-year holdout without reconciling duplicate keys.
- `event_calendar.csv`: dated local calendar anchors with government source URLs; no restriction/enforcement labels are inferred.
- `event_coverage_YEAR.csv`: per-station event availability. `event_coverage_2025.csv` describes XKDR's absent Diwali coverage, not the separate OpenCity holdout.
- `stations.csv`, source manifests, `quality_report.json`, `validation.json` and `sha256.json`: coordinates, attribution, coverage, limitations, validation evidence and integrity hashes.

## Time and label meaning

XKDR documents `collected_at` as naive Indian Standard Time. `source_time_ist` preserves that clock and `observation_time_utc` is its true UTC conversion. Source readings on the IST hour convert to UTC at minute 30.

`time` is the start of the UTC hour **containing** that published record, making a regular hourly key usable by the current feature builder. It does not claim the observation occurred at the bin start, nor that an unknown source averaging interval was shifted or reconstructed. Keep `observation_time_utc`, `label_semantics` and source fields when interpreting predictions. In particular, this target differs from the quarter-hour UTC means in the first package.

`available_no_earlier_than` is the bucket end. It is a conservative lower bound for using the record, not a verified publication timestamp. Actual reporting delays and original averaging-interval semantics still require verification before operational evaluation. Define forecast issue time explicitly and allow observations only after both their sampling interval and reporting delay have elapsed.

Weather is ERA5 reanalysis at the UTC bin start, about 30 minutes before the native observation timestamp. Nearby stations share four 0.25-degree grid locations. It is regional grid context, not neighborhood weather measurements or issued forecast weather. Mixing height is missing for January–June 2024; do not fill it with zero. Missing target values remain missing, and outliers have not been statistically removed.

## Baseline integration

Read only development years and pass an explicit input allowlist to the existing feature builder:

```python
import pandas as pd
from src.features.build_features import build_features

root = 'data/processed/multiyear_training/'
observations = pd.concat([
    pd.read_parquet(root + f'station_observations_{year}.parquet')
    for year in range(2017, 2025)
], ignore_index=True)
features = build_features(observations[[
    'station_id', 'time', 'pm25', 'temperature_2m',
    'relative_humidity_2m', 'wind_speed_10m', 'boundary_layer_height'
]])
```

The feature builder reindexes per station before lagging. Build target horizons and issue-time joins separately. Never use contemporaneous target PM2.5 as a predictor for itself, future pollution lags, future observations, audit metadata, or year/split fields accidentally included by selecting all numeric columns. Persist the preprocessing and feature definitions with the model.

## Burst model handoff

1. Treat 2017 as early baseline history. For each event year from 2018 onward, fit the baseline using only earlier observations, with all preprocessing fitted on that training period. Hold the target event out of baseline fitting. Decide and document whether event windows are excluded from baseline training to model a background component.
2. Generate predictions at the actual intended forecast horizons and issue times. Join those predictions to observed event labels on station, target time and horizon.
3. Compute `burst_residual = observed_pm25 - baseline_prediction`. Negative values are legitimate residuals; do not clip them automatically. This is event-associated error/excess, not identified firecracker causation.
4. Train the event model with only information available at issue time, such as event-relative time, recent available pollution, forecast weather and documented policy inputs where present. Do not use observed future PM2.5 or realized future weather for operational claims.
5. Suggested chronology: use early events for model fitting, 2023 for development validation and 2024 for a later development check. Fix choices before final 2025 evaluation; refitting on all development years after choices are frozen is permissible. Do not randomly split station-hours across festivals. Repeat station holdout separately without allowing held-out station labels into spatial features or calibration.
6. Only evaluate 2025 after acknowledging the source/label-definition transition and provisional timestamps. Report persistence, baseline-only and baseline-plus-burst on identical supported labels and horizons. Historical-weather experiments must be labeled retrospective.

The inventory window is local midnight 14 days before Diwali through 8 days after, end exclusive. `is_candidate_burst_window` is midnight one day before through three days after, end exclusive; this is an initial design parameter, not an established causal window or a known start of emissions. Choose windows within development data and perform sensitivity checks. Government holiday anchors do not specify exact firecracker timing.

## Attribution and remaining gaps

History: [India Air Quality Database, XKDR Forum](https://airquality.xkdr.org/), CPCB CAAQM, CC BY 4.0. Weather: [Open-Meteo](https://open-meteo.com/en/docs/historical-weather-api), Copernicus ERA5; preserve their attribution and usage terms. The source-unit text is retained and normalized to µg/m³ in `pm25_unit`; unusual publisher escaping in unit strings is not interpreted as a new unit.

2025: [OpenCity Delhi hourly reports](https://data.opencity.in/dataset/delhi-hourly-air-quality-reports), CPCB and listed contributor, catalog license Other (Public Domain). Original resource URLs and SHA-256 hashes are retained. All 313,635 nonmissing shared 2024 station-clock pairs match XKDR within 0.01 µg/m³, supporting the 2024 timestamp interpretation; that does not certify every 2025 record.

This package covers Delhi stations, not all NCR. Verified FIRMS, restriction/enforcement data, OSM context and ward ground truth are not included. Model accuracy, quantile calibration and causal attribution have not been established. Multiple stations do not create additional independent Diwalis.
