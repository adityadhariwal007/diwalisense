# Buzzy: local setup and checks

Buzzy explains the site's historical air data and gives room-size guidance for air purifiers. The supplied bee illustration floats and tilts using CSS 3D transforms. It is not a rigged 3D model. Motion can be paused and respects reduced-motion settings.

## Put your Gemini key here

Open `frontend/.env.local`. Keep the existing Supabase public settings and add:

```env
GEMINI_API_KEY=YOUR_KEY_HERE
GEMINI_MODEL=gemini-3.5-flash-lite
CHAT_ALLOWED_ORIGINS=http://127.0.0.1:5173,http://localhost:5173
```

Get the key in [Google AI Studio](https://aistudio.google.com/api-keys). Use a Free-tier project; do not enable billing to make this demo work. Never paste the key into chat, source files or any variable beginning with `VITE_`. The example file contains placeholders only; `.env.local` is ignored by Git.

From the repository root:

```bash
cd frontend
npm ci
npm run check:gemini
npm run dev
```

Open `http://127.0.0.1:5173`. The Vite server handles `/api/chat` locally; FastAPI is not needed for chat or Supabase-backed comparisons. Restart Vite after changing a key or model.

The model check lists Flash models visible to the supplied API key and checks that the selected model supports text generation. It does not send a chat or change billing. The local model-access check succeeded on 1 November 2026 for `gemini-3.5-flash-lite`. This verifies the saved key and model visibility, not generated replies or available free quota. Each new installation needs its own key and check.

## Model choice

Checked official Google docs on 1 November 2026: [models](https://ai.google.dev/gemini-api/docs/models), [pricing](https://ai.google.dev/gemini-api/docs/pricing), [model access API](https://ai.google.dev/api/models), [key security](https://ai.google.dev/gemini-api/docs/api-key).

The default is `gemini-3.5-flash-lite`, a documented stable Flash-Lite text model with a Free tier. `gemini-3.8-flash` is another documented Flash option, but is never selected automatically. The API verifies the configured model's supported methods before generation. Model access does not prove free quota; confirm the project's tier in AI Studio. No billing changes, paid tools or fallback models are enabled.

## Before any future Vercel deployment

No deployment is authorized by this change. `frontend/vercel.json` disables automatic Git deployments for the `codex/gemini-chat` branch. After explicit approval:

1. Apply `supabase/chat_rate_limit.sql` in the intended database. It creates private request counters and a server-only quota function. It does not store messages or raw IPs.
2. Set **server secrets** in Vercel → DiwaliSense → Settings → Environment Variables: `GEMINI_API_KEY` and `SUPABASE_SECRET_KEY`. The latter must be a Supabase secret key (or legacy service-role key), never a publishable key. Do not put either in `VITE_` variables.
3. Set `GEMINI_MODEL=gemini-3.5-flash-lite` and `CHAT_ALLOWED_ORIGINS=https://diwalisense.vercel.app`. Preview origins must be explicitly listed; wildcards are not used.
4. Keep the existing public Supabase URL/key settings. Confirm Free tier and model access. Then deploy only with approval and recheck the public flow.

The production endpoint fails closed until shared quotas are configured. Limits: 6 messages/minute and 40/day per daily-hashed IP, plus 500/day globally. Counters older than two days are removed on the next quota call. Local counters live in server memory and reset on restart. People sharing a network share a limit. Origin checks are browser protection, not user authentication; public endpoints still need quota monitoring before broad use.

## Test

```bash
npm test
npm run build
```

Try these in the local website:

- Select Rohini, then ask Buzzy to explain the air. It should label the readings as 2025.
- Ask: “Help me choose an air purifier.” It should ask for room area first.
- Reply: “200 sqft.” The server sizing guide gives at least 130 cfm (about 221 m³/h), assuming an 8-foot ceiling. Higher ceilings need more capacity. No brands or prices are available.
- Ask in Hindi/Hinglish and check that the answer matches your language.
- Close with Escape, reopen by keyboard, start a new chat, try on mobile, and pause bee motion.
- With no API key, confirm the honest setup message and working guidance link. Do not present that state as a working Gemini demo.

Tests cover conversation validation, quotas, shared-quota failure, provider failures, timeout handling, missing data, purifier calculations, origin/body limits, retrieved-data filtering and safe text rendering. Browser checks at a 390 × 844 viewport verified the missing-key error, retry focus, editing, Escape, keyboard reopening and session history. Real generated replies, the new SQL on a database and production behaviour still require setup and verification. The production build was also checked with fake server-secret canaries to ensure they do not appear in browser assets.

## Data and privacy

Only chat text and the chosen public area name are used. GPS, account details, cookies and private customer records are not sent to Gemini. If the location is found from GPS, the comparison page passes its nearby source name, not coordinates. The server fetches that source's public 2025 comparison from Supabase; unavailable data is labelled missing. Only known comparison dates and numeric pollution/coverage fields enter the model context; arbitrary database strings and extra fields are discarded.

Messages stay in React memory until reload/new chat; the app does not write chat history to Supabase, browser storage or application logs. Google processes submitted text under its own terms. Google's Free-tier pricing page says content may be used to improve its products. The panel warns visitors not to share private information.

Responses are plain text, not HTML. Only three fixed site links are clickable. There are no action tools, purchases, alerts or record changes. System rules restrict unsupported answers, but generative answers still need human review; this is not a medical service or a guarantee against hallucinations.

Purifier facts are shared between the guidance page and the bot in `frontend/src/content/air-help.json`, based on the [EPA guide](https://www.epa.gov/indoor-air-quality-iaq/guide-air-cleaners-home). Outdoor AQI does not determine room size, indoor exposure, a brand or a guaranteed protection level.

## Files changed

- `frontend/src/BeeChat.tsx`, `frontend/src/styles/chat.css`, `frontend/public/bee-guide.jpeg`: chat panel, supplied bee, 3D motion and keyboard/mobile behaviour.
- `frontend/api/chat.mjs`, `frontend/server/chat.mjs`: server endpoint, validation, origin checks, quotas, data lookup and Gemini requests.
- `frontend/server/check-gemini.mjs`, `chat.test.mjs`, `render.test.mjs`: model-access check and focused tests.
- `frontend/src/content/air-help.json`, `frontend/src/GuidelinesPage.tsx`: shared site facts and purifier guidance. `frontend/public/measured-metrics.json` makes the existing results link work on the static site.
- `frontend/src/App.tsx`, `frontend/src/ComparisonPage.tsx`: chat across pages and nearby source name passed without GPS.
- `frontend/.env.example`, `frontend/vite.config.ts`, `frontend/tsconfig.json`, `frontend/package.json`, `frontend/vercel.json`: local server, build/test configuration and placeholder settings.
- `supabase/chat_rate_limit.sql`: production-only shared quota setup, not applied.
- `docs/CHAT_SETUP.md`, `README.md`: chatbot setup and limits.

The earlier unfinished Python training edits were left untouched.
