# Round 2: working build and demo

## What is ready

The data added in GitHub commit `2323762` is pulled locally. Both development and holdout Parquet checksums match their supplied audit. `stations.csv` has a different hash from that audit; its actual checksum and discrepancy are recorded in `pulled_data_verification.json`. Station coordinates are supplied metadata, not independently surveyed positions.

The working flow is **2024 data → LightGBM background/residual models → FastAPI → React dashboard → measured 2025 comparison**. The preserved hero opens the working replay through **Explore forecast**.

Data files:

- `data/processed/training_package/development_2024.parquet`
- `data/processed/training_package/holdout_2025.parquet`
- `data/processed/training_package/stations.csv`
- `data/processed/kaggle_history/delhi_2017_2020.parquet` (staged, not merged)

## Run locally

Use Node 22.12+ and Python 3.11/3.12 for a new environment. The current laptop environment also ran successfully with Python 3.9 and compatible dependency versions. On macOS install `libomp` for LightGBM if needed.

```bash
python -m pip install -r requirements.txt
python -m src.models.hourly
cd frontend
npm ci
npm run build
cd ..
python -m uvicorn api.main:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000` for the built website and API on one server. The existing Vite preview is `http://127.0.0.1:5173`; it proxies `/api` to port 8000 during development. Restart the API after retraining. Training uses only local files and produces ignored artifacts in `artifacts/`; models are not uploaded to GitHub. After dependencies, data, training and frontend build are cached, the combined build needs no internet.

```bash
python -m pytest -q
cd frontend
npm test
npm run build
```

API: `/health`, `/stations`, `/forecast`, `/metrics`, `/priorities`, `/docs`. Missing artifacts return 503, invalid/missing station-times return a clear error, and unavailable hours are disabled in the UI.

## Model and evaluation contract

- Six-hour-ahead prediction of one target-hour PM2.5 value; replay targets occur every six UTC hours.
- Each source bin used by features ends no later than issue time. Unknown real publication latency remains a limitation.
- Features: previous pollution, prior 24-hour mean, prior weather/ventilation, calendar cycles and station coordinates. No target-hour pollution or weather is a feature.
- Background model: non-event Jan–Nov 2024. Burst targets: 2024 event residuals from a baseline fitted before October 2024. One independent training Diwali, pooled across monitors.
- Event window: -24 to +48 hours around 18:00 IST on Diwali, 31 October 2024 / 20 October 2025. Calendar references: [2024 government calendar](https://www.lpsc.gov.in/holidaysBangalore2024.html), [2025 government calendar](https://www.cag.gov.in/ae/mumbai/en/page-ae-mumbai-holiday-list-2021).
- December 2024 expands total-model intervals using pooled calibration errors. It does not guarantee event-specific coverage.
- Fitted weights are saved and hashed before reading the 2025 holdout. No hyperparameters are selected from 2025 scores.
- 39 leave-one-station-out checks exclude station rows from fitting and calibration. They retain the station’s historical readings as inference inputs: this is not a test of sensor-free neighborhoods.
- Priorities rank station areas for review. No ward estimates, safe cracker windows or medical advice are implemented.

The chart contains **separate rolling six-hour-ahead predictions** with different issue times. It is not a single 48-hour-ahead forecast.

## Results to tell mentors

| 2025 test | Combined MAE | Persistence MAE | Combined RMSE | Persistence RMSE |
|---|---:|---:|---:|---:|
| All 50,010 rows | 28.365 | 43.819 | 48.063 | 71.830 |
| Diwali-window 389 rows | 86.409 | 148.319 | 125.418 | 208.602 |

Diwali baseline-only MAE is **81.491**, better than the combined **86.409**; the burst still needs improvement. Interval coverage is **88.45% overall** and **51.93% around Diwali**. Do not call the event interval reliable. AQI-category accuracy remains **[TO BE MEASURED]**: hourly PM2.5 is not 24-hour AQI.

## Two-minute demo

1. Open the website and select **Explore forecast**. Say “This is a historical 2025 holdout replay, not live 2026 conditions.”
2. Start with **Alipur**, **20 October 2025**, **23:30 IST**. Point out issue time, median, range, background and event adjustment.
3. Click **Before Diwali** and **After Diwali**. Explain that each point has its own issue time and uses only prior bins.
4. Show observed values on the chart for comparison, then the measured model/persistence table.
5. Switch to **Officer** to show station-area priorities. Mention missing stations and that these are not ward measurements.
6. Close with the weak Diwali interval coverage and single-event training limitation, then the next improvement.

## Four-slide pitch draft

**Slide 1 — The problem:** Pollution changes across Delhi during Diwali. We forecast monitoring areas and show uncertainty. Most neighborhoods still have no sensor.

**Slide 2 — Working approach:** Prior pollution + weather → background model; 2024 event residual → Diwali adjustment; combined forecast → FastAPI → resident/officer dashboard. Target: six hours ahead.

**Slide 3 — Working demo and evidence:** Show the replay, uncertainty chart and priority list. Report the measured comparison above. Show both annual and event-window error; do not hide weaker component or interval results.

**Slide 4 — Limits and next steps:** One training Diwali, reanalysis weather and uncertain reporting latency; no validated ward estimates. Resolve historical timezone/station mapping, add earlier events, improve event intervals, then validate spatial transfer.

## Suggested split for the four members

- Aditya: run the website/API and lead the live demo.
- Maanvik: explain the two-model flow, issue-time features and persistence comparison.
- Palakshi: explain data sources, quality audits, missing data and uncertainty.
- Manveer: prepare the four pitch slides, time the demo and confirm checkpoint timing with organizers.

The supplied screenshots conflict: one says 5 AM; another says 6–7 AM. Confirm the current deadline directly with organizers.
