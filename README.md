# DiwaliSense

Compare air pollution before, during and after Diwali.

Built by **Team Clauders** for the **RootAccess** environment and sustainability hackathon.

**[Open the website](https://diwalisense.vercel.app)** · **[Try the comparison](https://diwalisense.vercel.app/#compare)**

## What it does

Pollution can rise around Diwali and stay high for several days. DiwaliSense helps people see how the air changed near their area in Delhi.

- Share your location or search for a Delhi area. Nearby air data is selected automatically.
- Compare **before Diwali, Diwali day and after Diwali** on one screen.
- Switch between recorded pollution and AI estimates, and see both on a graph.
- View a rough cigarette comparison for a day, week and year.
- Read simple guidance for **students, teachers and officers**.

The website currently shows **Diwali 2025 data**, not today's air quality.

## How the AI works

We split the estimate into two parts:

1. **Usual pollution:** estimate pollution from recent readings and weather, such as wind, temperature and humidity.
2. **Diwali increase:** estimate the extra rise seen around Diwali.

Think of a bucket: everyday pollution fills it, Diwali may add more, and moving air helps clear it.

The current model was trained using **2024 data** and checked against **2025 readings**. The website loads saved results from Supabase, so it does not need to train a model when someone opens it.

## What we use

| Part | Tools |
|---|---|
| Website | React, Vite, TypeScript, Tailwind CSS |
| Data and AI | PythonLightGBM |

| Online database | Supabase |
| Website hosting | Vercel |

Historical air readings come from **CPCB data shared through XKDR Forum and OpenCity**. Weather comes from **Open-Meteo / Copernicus ERA5**. The database includes daily air records from 2017–2025; the current model uses the smaller training period described above.

## Run the website locally

Use **Node.js 24** and access to the project's Supabase public settings.

```bash
git clone https://github.com/adityadhariwal007/diwalisense.git
cd diwalisense/frontend
npm ci
cp .env.example .env.local
```

Fill in these two values in `frontend/.env.local`:

```env
VITE_SUPABASE_URL=https://YOUR_PROJECT.supabase.co
VITE_SUPABASE_PUBLISHABLE_KEY=sb_publishable_REPLACE_ME
```

Use the **publishable key**, never an admin or service-role key. Keep `.env.local` out of Git.

```bash
npm run dev
```

Open the local address printed in the terminal.

To check the code and build the website:

```bash
npm test
npm run build
```

## Keep these limits in mind

- Nearby readings are **not measurements at your home**. Most neighborhoods have no sensor.
- The displayed AQI estimate uses **PM2.5 only**—tiny particles in the air. It is not the full official AQI.
- The extra Diwali part is still experimental and does not always improve the result. It cannot prove how much pollution came only from firecrackers.
- Missing readings and uncertain timestamps can affect comparisons. More years in the database do not mean the current model has been trained on all of them.
- The cigarette numbers are a rough comparison, not actual smoking or a personal health prediction. Week and year totals assume the same pollution every day.
- GPS coordinates stay in your browser in the Supabase version. Visitors can read the air data but cannot change it.

## More details

- [Cloud setup and database](docs/CLOUD_SETUP.md)
- [Buzzy chatbot setup and checks](docs/CHAT_SETUP.md)
- [Full architecture and planned features](docs/architecture.md)
- [Measured model results](docs/measured_metrics.json)
- [Local Python demo setup](docs/round2.md)

## Team and license

**Clauders:** Aditya, Maanvik, Palakshi and Manveer.

Code: [MIT License](LICENSE). Data and media keep their own licenses; rights to redistribute the supplied background video have not been verified.
