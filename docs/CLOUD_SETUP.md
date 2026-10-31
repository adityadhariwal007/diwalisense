# Cloud deployment

The Vite website reads public environmental data from Supabase. PostgreSQL row-level security permits reads only; browser users cannot insert, update or delete rows. Only the public publishable key is used by the website. User GPS coordinates stay in the browser; the selected source ID is sent to Supabase.

## Data stored

- `air_locations`: 39 source locations and coordinates.
- `daily_air`: daily PM2.5 means from the curated 2017–2024 development files and the separate OpenCity 2025 holdout. At least 16 available readings per local calendar day. These are available-reading averages; source averaging intervals and reporting delays remain uncertain. The provisional 2025 timestamp interpretation remains a limitation.
- `comparison_snapshots`: three-day 2025 comparisons generated using the existing 2024 prototype artifact. These are precomputed historical estimates, not live inference. The comparison retains its original 24-hour windows ending 23:30 IST, which differ from the daily history's calendar days.

Raw hourly data and weather remain in the repository. This deployment does not upload all raw rows or train a new model. Later model versions must explicitly regenerate the snapshots.

Source attribution: XKDR Forum / CPCB (CC BY 4.0); OpenCity / CPCB (see repository source manifests). Weather used by the prototype: Open-Meteo / Copernicus ERA5. Preserve the existing source manifests and data-quality audits.

## Local setup

Copy `frontend/.env.example` to `frontend/.env.local`, fill the Supabase URL and publishable key, then run `npm ci` and `npm run dev` inside `frontend`. Without those variables, the existing local FastAPI mode remains available.

## Rebuilding the data

Run `.venv/bin/python -m scripts.export_cloud_data` from the repository root with the trusted existing `artifacts/hourly_model.joblib` present. It writes `.presentation-build/cloud-data.json`. Apply `supabase/schema.sql` to an empty project once, then import the three collections with an administrator connection. Never enable anonymous writes to import data. Keep admin credentials outside the frontend and Git.

Vercel project: `diwalisense`; root directory: `frontend`; Node 24; build: `npm run build`; output: `dist`. Set `VITE_SUPABASE_URL` and `VITE_SUPABASE_PUBLISHABLE_KEY` in Vercel. No service-role key is needed. This deployment is made from local source files without pushing changes to GitHub.

Verified production URL: https://diwalisense.vercel.app
Supabase project ref: `syjhjgdbydtmxlczbzvp` (Mumbai). Imported: 104,838 daily records, 39 locations, 39 comparison snapshots. Deployment ID: `dpl_861EPeByG1GBniwFAnEjC6gD9LUH`. Anonymous SELECT succeeded; an actual PATCH was denied (401); security advisor reported no findings.
