import { useState } from 'react';
import PageHeader from './PageHeader';
import airHelp from './content/air-help.json';

const WHO = 'https://www.who.int/news-room/questions-and-answers/item/air-pollution-personal-interventions-and-risk-communication';
const CAQM = 'https://caqm.nic.in/';
const OFFICERS = 'https://www.pib.gov.in/PressReleasePage.aspx?PRID=2272556&lang=1&reg=3';
const SCHOOL = 'https://www.pib.gov.in/PressReleasePage.aspx?PRID=2078839&lang=2&reg=48';
const guidance = {
  students: {
    label: 'Students', title: 'Less smoke. More care.',
    steps: [
      ['Choose a cleaner place to play.', 'When pollution is high, ask for an indoor option instead of hard outdoor exercise.'],
      ['Keep away from smoke.', 'Avoid smoky areas and heavy traffic when you can. Ask an adult to help find a cleaner route.'],
      ['Tell an adult if you feel unwell.', 'Speak up if breathing feels uncomfortable. If you have a doctor’s care plan, follow it.'],
    ], source: WHO, sourceName: 'WHO guidance on reducing exposure',
  },
  teachers: {
    label: 'Teachers', title: 'Make cleaner-air choices at school.',
    steps: [
      ['Check the official air report.', 'Look at current local air-quality updates before sports, assemblies and outdoor trips.'],
      ['Adjust outdoor activities.', 'Choose a cleaner time or place for demanding exercise. Take extra care of children with breathing problems.'],
      ['Keep families informed.', 'Share the school’s current instructions. Follow local government orders for classes and closures.'],
    ], source: WHO, sourceName: 'WHO guidance on activity and exposure',
  },
  officers: {
    label: 'Officers', title: 'Check. Act. Follow up.',
    steps: [
      ['Start with official reports.', 'Check official AQI and the current CAQM directions before planning action.'],
      ['Check local pollution sources.', 'Review dust, open-burning and construction complaints. Focus inspections on reported hotspots.'],
      ['Record what happens next.', 'Track inspections and follow-up work. Share clear updates with schools and residents.'],
    ], source: OFFICERS, sourceName: 'CAQM enforcement priorities, via PIB',
  },
};

export default function GuidelinesPage() {
  const [audience, setAudience] = useState<keyof typeof guidance>('students');
  const selected = guidance[audience];
  return <div className="simple-page"><PageHeader active="guidelines" /><main className="guidance-main">
    <p className="year-label">When air pollution is high</p><h1 className="font-display">Small steps.<br />Better protection.</h1><p className="page-lead">Clear guidance for the people who live, learn and work here.</p>
    <div className="audience-switch" aria-label="Who is this guidance for?">{(Object.keys(guidance) as (keyof typeof guidance)[]).map(key => <button key={key} aria-pressed={audience === key} onClick={() => setAudience(key)}>{guidance[key].label}</button>)}</div>
    <section className="guidance-content" aria-live="polite"><h2>{selected.title}</h2><ol>{selected.steps.map(([title, body], index) => <li key={title}><span aria-hidden="true">{index + 1}</span><div><h3>{title}</h3><p>{body}</p></div></li>)}</ol><a className="text-button" href={selected.source} target="_blank" rel="noreferrer">{selected.sourceName}</a>{audience === 'teachers' && <a className="text-button source-extra" href={SCHOOL} target="_blank" rel="noreferrer">School decisions must follow official local orders</a>}</section>
    <section className="purifier-guide" aria-labelledby="purifier-title"><h2 id="purifier-title">{airHelp.purifier.title}</h2><p>{airHelp.purifier.intro}</p><ul>{airHelp.purifier.steps.map(step => <li key={step}>{step}</li>)}</ul><p>Ask Buzzy for help with room size. No brand or price list is available.</p><a href={airHelp.purifier.source} target="_blank" rel="noreferrer">{airHelp.purifier.sourceName}</a></section>
    <div className="guidance-notice"><h2>Use today’s official advice.</h2><p>This page gives general guidance. The Diwali comparison uses 2025 data and cannot tell you today’s conditions.</p><a href={CAQM} target="_blank" rel="noreferrer">Check current CAQM directions</a></div>
    <a className="solid-button" href="#compare">Back to the air comparison</a>
  </main></div>;
}

export function AboutDataPage() {
  return <div className="simple-page"><PageHeader active="data" /><main className="data-main"><p className="year-label">Plain facts about the numbers</p><h1 className="font-display">What the data<br />can tell you.</h1>
    <section><h2>This is a 2025 comparison.</h2><p>Before Diwali means 19 October, Diwali means 20 October, and after Diwali means 21 October 2025. These are historical records and AI estimates, not live air conditions.</p></section>
    <section><h2>Nearby is an estimate for your area.</h2><p>Location is used to find a nearby Delhi monitoring location with usable data for all three days where possible. The same source is used across the comparison. It is not a measurement at your house. Areas more than 35 km from our sources are outside this demo’s coverage.</p></section>
    <section><h2>AQI here uses PM2.5 only.</h2><p>PM2.5 means very small particles in the air. We calculate a PM2.5-based AQI estimate from a 24-hour mean, with at least 16 hourly readings. The daily window ends at 23:30 IST. Full official AQI needs other pollutants too. Severe pollution is shown as the 401–500 band rather than an invented exact number.</p><a href="https://ies.gov.in/arthapedia/concept/national-air-quality-index" target="_blank" rel="noreferrer">Government explanation of AQI</a></section>
    <section><h2>The AI is still being tested.</h2><p>Recorded values come from the pulled Delhi data package. AI daily values average separate hourly predictions, each made six hours before its target hour. They are not a single day-ahead forecast. The model learned from 2024, with only one training Diwali. Daily AQI accuracy has not been measured.</p><p>The hourly model’s Diwali ranges covered only 51.9% of test readings. Its burst component did not consistently improve the background model. Weather comes from historical reanalysis; real reporting delays are unknown.</p><a href="/measured-metrics.json" target="_blank" rel="noreferrer">See the measured model results</a></section>
    <section><h2>The cigarette comparison is a rough guide.</h2><p>Berkeley Earth’s rule of thumb compares a daily PM2.5 concentration of 22 µg/m³ with roughly one cigarette per day. We divide the selected daily PM2.5 value by 22. Week and year totals multiply that result by 7 and 365, assuming unchanged pollution.</p><p>This is a broad population-level comparison, not the cigarettes you smoked or a prediction of your personal health. It does not mean pollution and cigarette smoke contain the same chemicals.</p><a href="https://berkeleyearth.org/air-pollution-and-cigarette-equivalence/" target="_blank" rel="noreferrer">Read Berkeley Earth’s explanation</a></section>
    <section><h2>Sources and checks</h2><p>Air observations: the repository’s OpenCity Delhi package for 2024–2025. The database also holds daily 2017–2025 records from the curated XKDR/CPCB and OpenCity/CPCB files. The current displayed AI estimates still use the 2024-trained model. Both main Parquet file hashes match their audit; the supplied station-metadata hash does not. Source metadata has not been independently confirmed for every location.</p><p>The cigarette illustration is AI-generated. Smoke is decorative and can be paused. Device location is requested only when you press “Use my location”; in the Supabase version, coordinates stay in your browser. Buzzy receives only the nearby source name when it is available.</p></section>
    <a className="solid-button" href="#compare">Back to the air comparison</a>
  </main></div>;
}
