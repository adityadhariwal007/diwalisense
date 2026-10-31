# Training data handoff

**Latest collection:** use [the multi-year training handoff](../data/processed/multiyear_training/README.md) for the expanded 2017–2024 development history and separately attributed 2025 holdout. The sections below describe the initial package and remain as its provenance. Do not concatenate the initial and expanded versions; their measurements overlap and their label definitions differ.

Start with `data/processed/training_package/development_2024.parquet`.
Keep `holdout_2025.parquet` untouched for final evaluation. These are retrospective experimental inputs, not evidence of operational forecast accuracy. The curated Parquet files and audit metadata are allowed in Git (approximately 25 MB total). Raw downloads, duplicate CSV exports, intermediate weather tables and the ZIP remain ignored. The ZIP provides an alternative full processed handoff.

The committed selection includes development/holdout observations with joined weather, excluded year-boundary bins, station metadata, coverage, quality reports and source provenance. The early Kaggle Parquet is explicitly historical staging, not ready for direct concatenation. `quality_report.json` also lists hashes for optional local intermediate files; those files can be regenerated and are not all committed.

## Delivered datasets

| Directory | Contents | Readiness |
|---|---|---|
| `data/raw/opencity/` | Original 39 station concentration CSV exports, 2024–2025 | Immutable source cache |
| `data/processed/opencity/` | Original UTC-labeled hourly aggregates and source manifest | Audit only: do not join these provisional timestamps to weather |
| `data/processed/training_package/` | UTC-hour concentration bins, station coordinates, temperature, RH, wind and mixing height; separate development/holdout | Retrospective starter; timestamp interpretation is supported by sampled cross-source comparisons, not confirmed by the publisher |
| `data/raw/kaggle/` | Original archive and license catalog | Source cache |
| `data/processed/kaggle_history/` | Delhi station-hour PM2.5, 2017–July 2020, Parquet and compressed CSV | Staging: resolve timezone and station-ID crosswalk before merging |

The OpenCity download contains 684,216 original hourly bins, of which 632,255 have at least three valid quarter-hour PM2.5 samples. These are **pre-correction counts**. The corrected training package has different bin boundaries; use its `quality_report.json` and `coverage.csv` for final counts. Kaggle staging contains 913,203 records, 766,782 nonmissing PM2.5 values, and 38 stations. Missing values remain missing. Record counts are not independent festival events.

## Load into the current feature builder

```python
import pandas as pd
from src.features.build_features import build_features

data = pd.read_parquet('data/processed/training_package/development_2024.parquet')
columns = ['station_id', 'time', 'pm25', 'temperature_2m',
           'relative_humidity_2m', 'wind_speed_10m', 'boundary_layer_height']
features = build_features(data[columns])
```

Use only an explicit feature allowlist. Do not feed the target `pm25`, audit fields, split labels, future weather, or future observations into predictors by accident. For horizons beyond one step, the teammate implementing training must define issue time, target shift, reporting delays, and which weather inputs were available then. Reanalysis weather is not an archived weather forecast.

## Timestamp decision and aggregation

OpenCity files show `+0000`, but their clock-hour means exactly matched available XKDR values in sampled station-days when compared as **IST wall-clock**. XKDR explicitly documents its timestamps as IST. `timestamp_audit.json` records the checks. Checks cover three station-days in 2024; 2025 has not been independently confirmed. This is a documented inference, not a provider-certified correction.

The prepared package strips the misleading suffix, interprets the clock as Asia/Kolkata, converts each original quarter-hour sample to UTC, then averages into left-closed UTC-hour bins. It does **not** round converted hourly means. At least three nonnegative numeric samples are required. Repeated quarter-hour values count as available records, not independent measurements. Invalid timestamp separator rows are excluded; raw files remain intact. No statistical outliers are removed and no targets are imputed.

Each value represents an interval `[time, time + 1 hour)`. `available_no_earlier_than` gives the interval end, not the actual publication time. Actual reporting latency is unknown. Local calendar year determines the split. Bins spanning a local year boundary are placed in `year_boundary_excluded`, preventing a mixed 2024/2025 hour from entering training. Calendar/event features should use Asia/Kolkata.

## Columns and units

| Column | Meaning |
|---|---|
| `station_id`, `time` | Unique CPCB station / UTC interval-start key |
| `pm25` | Concentration in µg/m³, not AQI |
| `sample_count` | Valid nonnegative quarter-hour observations in the bin |
| `temperature_2m` | Open-Meteo historical grid temperature, °C |
| `relative_humidity_2m` | Historical grid relative humidity, % |
| `wind_speed_10m` | Historical grid wind speed, m/s |
| `boundary_layer_height` | Historical grid mixing height, m |
| `weather_grid_latitude`, `weather_grid_longitude` | Returned weather grid location; may be shared between stations |
| `split`, `timestamp_status`, `weather_type`, `source_resource_id` | Audit fields; exclude from model predictors |

Weather was requested at each station's coordinates. Nearby stations may share the same grid cell; this does not supply neighborhood-scale weather observations. The raw JSON includes returned units and coordinates. The concentration source manifest records source URLs and SHA-256 hashes. The package report hashes its output files.

**Observed weather gap:** the downloaded archive returns null boundary-layer height for January–June 2024 at all 39 sites. Temperature, humidity and wind are present. A direct ERA5 check also returned null mixing height. These nulls remain null; do not replace them with zero. Use complete rows for a ventilation-dependent experiment or explicitly design a model that handles the missing feature. This reduces usable complete-case rows and must be reported.

## Sources and attribution

- [OpenCity Delhi archive](https://data.opencity.in/dataset/delhi-hourly-air-quality-reports): preserve attribution to OpenCity, the listed contributor and CPCB. Cached catalog lists `Other (Public Domain)`. Only the 2024–2025 concentration exports are used. Earlier AQI matrices are **not** PM2.5 labels.
- [India Air Quality Database, XKDR Forum](https://airquality.xkdr.org/): station metadata and small timestamp comparison samples. CC BY 4.0; credit XKDR Forum, CPCB CAAQM and US Department of State/AirNow. This package's stations are CPCB records.
- [Open-Meteo historical weather](https://open-meteo.com/en/docs/historical-weather-api): credit Open-Meteo and its weather data providers. Historical reanalysis supports retrospective experiments. Observe API usage terms when refreshing or commercializing.
- [Rohan Rao, Air Quality Data in India](https://www.kaggle.com/datasets/rohanrao/air-quality-data-in-india): CPCB-derived historical fallback; Kaggle API catalog identifies CC0: Public Domain. Metadata is cached alongside the original download.

## Remaining work before the full README training scope is met

1. Obtain verified concentration history for **2021–2023**, plus the latter half of 2020. A personal XKDR key is a promising bulk-download route; actual Delhi station/year coverage must still be audited. Save it only in `.env` as `XKDR_API_KEY`.
2. Resolve Kaggle IDs to CPCB sites using station names and locations, confirm timezone and interval semantics, then fetch matching weather. Do not concatenate the staging data directly into the recent dataset.
3. Confirm the OpenCity timestamp convention with the publisher/upstream exporter, especially 2025. Keep the current interpretation visible in any experimental result.
4. Add verified Diwali dates and year/location-specific restriction records. Unknown restrictions must remain unknown. Do not infer enforcement from policy text.
5. Add historical regional FIRMS observations if required by the chosen model. Missing fire data must not be encoded as zero detections.
6. Collect ward boundaries and OSM context for spatial tasks separately. The current observations cover Delhi stations, not all NCR or ward-level ground truth.
7. Evaluate gaps and extreme readings, create rolling time folds within development data, and keep the 2025 holdout out of tuning. One development-year Diwali cannot establish general event-model performance.

## Reproduction

Run from the repository root with its Python environment:

```powershell
.\.venv\Scripts\python.exe scripts\download_training_sources.py
.\.venv\Scripts\python.exe scripts\collect_training_data.py
.\.venv\Scripts\python.exe scripts\prepare_training_package.py
.\.venv\Scripts\python.exe scripts\prepare_kaggle_history.py
```

The latter two use cached source downloads. `prepare_training_package.py` fetches weather and comparison samples if absent. The initial Kaggle ZIP and XKDR station catalog must be downloaded first; see `scripts/download_training_sources.py`. Re-running uses caches, so explicit refresh/versioning is required to pick up upstream changes.
