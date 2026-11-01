import { useEffect, useState } from 'react';
import PageHeader from './PageHeader';
import { cloudData, cloudEnabled } from './cloud-data';

const API = import.meta.env.DEV ? '/api' : '';
export type LocationChoice = { name: string; latitude: number; longitude: number };
type AQI = { display: string; label: string; tone: string };
type Reading = { pm25: number | null; aqi: AQI | null; cigarettes: { day: number; week: number; year: number } | null };
type Phase = { label: string; date: string; recorded: Reading; estimated: Reading; observed_hours: number; predicted_hours: number };
export type Comparison = { area: string; distance_km: number; phases: Phase[]; details: Record<string, string> };

async function getJson<T>(path: string, signal: AbortSignal, body?: unknown): Promise<T> {
  if (cloudEnabled) return await cloudData(path, signal, body) as T;
  const response = await fetch(`${API}${path}`, body ? { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body), signal } : { signal });
  let data;
  try { data = await response.json(); } catch { throw new Error('Air data is unavailable. Please try again.'); }
  if (response.status === 503) throw new Error('Air data is not ready yet. Please try again shortly.');
  if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Could not load the air data. Please try again.');
  return data as T;
}

function AirGraph({ phases }: { phases: Phase[] }) {
  const maximum = Math.ceil(Math.max(100, ...phases.flatMap(phase => [phase.recorded.pm25 || 0, phase.estimated.pm25 || 0])) / 100) * 100;
  const x = (index: number) => 90 + index * 290;
  const y = (value: number) => 240 - value / maximum * 190;
  const lines = (mode: 'recorded' | 'estimated') => {
    const segments: string[][] = [[]];
    phases.forEach((phase, index) => {
      const value = phase[mode].pm25;
      if (value === null) segments.push([]);
      else segments[segments.length - 1].push(`${x(index)},${y(value)}`);
    });
    return segments.filter(segment => segment.length > 1).map(segment => segment.join(' '));
  };
  return <section className="air-graph" aria-labelledby="graph-title">
    <div className="section-top"><h2 id="graph-title">How the air changed</h2><span>PM2.5 · µg/m³</span></div>
    <p>Higher means more tiny particles in the air.</p>
    <p className="graph-scale">Scale: 0–{maximum} µg/m³</p>
    <svg viewBox="0 0 760 270" role="img" aria-label="Before, during and after Diwali: recorded PM2.5 compared with AI estimates. Values are listed below.">
      {[0, 0.5, 1].map(fraction => <g key={fraction}><line x1="72" x2="690" y1={y(maximum * fraction)} y2={y(maximum * fraction)} stroke="#dbe2d9" /><text x="56" y={y(maximum * fraction) + 6} textAnchor="end" fontSize="17" fill="#5d685f">{Math.round(maximum * fraction)}</text></g>)}
      {(['recorded', 'estimated'] as const).map(mode => <g key={mode} stroke={mode === 'recorded' ? '#294d37' : '#af7850'} fill="none">{lines(mode).map((line, index) => <polyline key={index} points={line} strokeWidth="4" strokeDasharray={mode === 'estimated' ? '8 7' : undefined} />)}{phases.map((phase, index) => phase[mode].pm25 !== null && <circle key={phase.date} cx={x(index)} cy={y(phase[mode].pm25!)} r="6" fill={mode === 'recorded' ? '#294d37' : '#af7850'} />)}</g>)}
    </svg>
    <div className="graph-period-labels">{phases.map(phase => <span key={phase.date}>{phase.label}</span>)}</div>
    <div className="air-legend"><span><i className="legend-solid" /> Recorded</span><span><i className="legend-dashed" /> AI estimate</span></div>
    <details className="simple-details"><summary>Read the graph values</summary><div className="readable-table"><table><thead><tr><th>Day</th><th>Recorded PM2.5</th><th>AI PM2.5</th></tr></thead><tbody>{phases.map(phase => <tr key={phase.date}><td>{phase.label}</td><td>{phase.recorded.pm25 ?? 'Not enough data'}</td><td>{phase.estimated.pm25 ?? 'Not enough data'}</td></tr>)}</tbody></table></div></details>
  </section>;
}

export default function ComparisonPage({ location, onLocationChange, onResolvedArea }: { location: LocationChoice | null; onLocationChange: (value: LocationChoice) => void; onResolvedArea?: (name: string) => void }) {
  const [areas, setAreas] = useState<LocationChoice[]>([]);
  const [query, setQuery] = useState('');
  const [data, setData] = useState<Comparison | null>(null);
  const [loading, setLoading] = useState(false);
  const [locating, setLocating] = useState(false);
  const [error, setError] = useState('');
  const [locationError, setLocationError] = useState('');
  const [mode, setMode] = useState<'recorded' | 'estimated'>('estimated');
  const [selectedDay, setSelectedDay] = useState(1);
  const [retry, setRetry] = useState(0);
  const [changingLocation, setChangingLocation] = useState(!location);

  useEffect(() => {
    const controller = new AbortController();
    getJson<LocationChoice[]>('/locations', controller.signal).then(result => { setAreas(result); setLocationError(''); }).catch(reason => { if (reason.name !== 'AbortError') setLocationError('Area search is unavailable. You can still use your location or retry.'); });
    return () => controller.abort();
  }, [retry]);

  useEffect(() => {
    if (!location) return;
    const controller = new AbortController();
    setLoading(true); setError(''); setData(null);
    getJson<Comparison>('/comparison', controller.signal, { latitude: location.latitude, longitude: location.longitude })
      .then(result => { setData(result); onResolvedArea?.(result.area); }).catch(reason => { if (reason.name !== 'AbortError') { setError(reason.message); setChangingLocation(true); } })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [location, retry, onResolvedArea]);

  const choose = (area: LocationChoice) => { onLocationChange(area); setChangingLocation(false); setQuery(''); setLocationError(''); };
  const useLocation = () => {
    setLocationError('');
    if (!navigator.geolocation) { setLocationError('This browser cannot find your location. Type your Delhi area below.'); return; }
    setLocating(true);
    navigator.geolocation.getCurrentPosition(position => {
      choose({ name: 'Your location', latitude: position.coords.latitude, longitude: position.coords.longitude }); setLocating(false);
    }, () => { setLocating(false); setLocationError('Location could not be shared. Type your Delhi area below.'); }, { enableHighAccuracy: false, timeout: 12000, maximumAge: 300000 });
  };
  const matches = query.trim() ? areas.filter(area => area.name.toLowerCase().includes(query.trim().toLowerCase())).slice(0, 5) : [];
  const selected = data?.phases[selectedDay];
  const reading = selected?.[mode];

  return <div className="simple-page"><PageHeader active="compare" /><main className="comparison-main">
    <div className="comparison-heading"><p className="year-label">Diwali 2025 · Not live</p><h1 className="font-display">Air around Diwali.</h1><p>Compare the air before, during and after Diwali.</p></div>
    {(!location || changingLocation) && <section className="location-panel" aria-labelledby="location-heading">
      <h2 id="location-heading">Where are you?</h2><p>Share your location, or enter your area in Delhi.</p>
      <button className="solid-button location-button" onClick={useLocation} disabled={locating}>{locating ? 'Finding your location…' : 'Use my location'}</button>
      <p className="location-privacy">Your location helps find nearby air data. It is not saved.</p>
      <label htmlFor="area-search">Or type your area</label><input id="area-search" type="search" placeholder="Try Rohini, ITO or Alipur" value={query} onChange={event => setQuery(event.target.value)} autoComplete="off" />
      {!!matches.length && <ul className="area-results" aria-label="Matching areas">{matches.map(area => <li key={area.name}><button onClick={() => choose(area)}>{area.name}<span>Delhi</span></button></li>)}</ul>}
      {query && !matches.length && <p>No matching Delhi area. Try a nearby area name.</p>}
      {locationError && <p role="alert">{locationError}</p>}
      <button className="text-button demo-button" onClick={() => choose({ name: 'Rohini', latitude: 28.73, longitude: 77.12 })}>Try the Delhi demo</button>
    </section>}
    {location && <div className="location-summary"><span>{location.name === 'Your location' ? 'Your location' : `${location.name}, Delhi`}</span><button className="text-button" onClick={() => setChangingLocation(value => !value)}>{changingLocation ? 'Hide location search' : 'Change location'}</button></div>}
    {loading && <p className="simple-status" role="status">Finding nearby air data…</p>}
    {error && <div className="simple-error" role="alert"><p>{error}</p><button className="text-button" onClick={() => setRetry(value => value + 1)}>Try again</button></div>}
    {data && <>
      <div className="comparison-top"><div><h2>Three days. One comparison.</h2><p>Nearby data near {data.area}, {data.distance_km.toFixed(1)} km away.</p></div><div className="reading-switch" aria-label="Choose readings"><button aria-pressed={mode === 'recorded'} onClick={() => setMode('recorded')}>Recorded</button><button aria-pressed={mode === 'estimated'} onClick={() => setMode('estimated')}>AI estimate</button></div></div>
      <div className="phase-cards" aria-label="Compare the three days">{data.phases.map((phase, index) => {
        const value = phase[mode];
        return <button key={phase.date} className={`phase-card ${selectedDay === index ? 'selected-phase' : ''}`} aria-pressed={selectedDay === index} onClick={() => setSelectedDay(index)}><span className="phase-name">{phase.label}</span><span className="phase-date">{new Date(phase.date + 'T12:00:00').toLocaleDateString('en-IN', { day: 'numeric', month: 'long' })}</span><strong className={`aqi-number ${value.aqi?.display.includes("–") ? "aqi-band" : ""}`}>{value.aqi?.display || '—'}</strong><span className={`air-status ${value.aqi?.tone || ''}`}>{value.aqi?.label || 'Not enough data'}</span><span className="pm-value">{value.pm25 === null ? 'More readings needed' : `PM2.5: ${value.pm25.toFixed(1)} µg/m³`}</span></button>;
      })}</div>
      <AirGraph phases={data.phases} />
      <section className="exposure-section" aria-labelledby="exposure-title"><div className="exposure-intro"><p className="selected-day-label">{selected?.label} · {mode === 'recorded' ? 'Recorded pollution' : 'AI estimate'}</p><h2 id="exposure-title" className="font-display">What does that<br />mean in cigarettes?</h2><p>A rough way to picture fine-particle pollution. This is not actual smoking or your personal health risk.</p><div className="cigarette-visual"><img src="/cigarette.png" alt="A burning cigarette used to illustrate the pollution comparison" /><div className="smoke-trails" aria-hidden="true"><i /></div></div></div><div className="exposure-numbers"><h3>If every day had this pollution</h3>{reading?.cigarettes ? <dl>{([['day', 'In one day'], ['week', 'In one week'], ['year', 'In one year']] as const).map(([key, label]) => <div key={key}><dt>{label}</dt><dd>{reading.cigarettes![key].toLocaleString('en-IN', { maximumFractionDigits: key === 'year' ? 0 : 1 })}<span> cigarettes</span></dd></div>)}</dl> : <p>Not enough daily data for this comparison.</p>}<p>Week and year totals assume the same pollution every day. They are not forecasts.</p><a className="text-button" href="https://berkeleyearth.org/air-pollution-and-cigarette-equivalence/" target="_blank" rel="noreferrer">How Berkeley Earth estimates this</a></div></section>
      <section className="guidance-banner"><div><h2>High pollution? Know what to do.</h2><p>Simple guidance for students, teachers and officers.</p></div><a className="solid-button" href="#guidelines">Read the guidance</a></section>
      <footer className="comparison-footer"><span>2025 data. Nearby estimates, not live conditions.</span><a href="#data">About the data and limits</a></footer>
    </>}
  </main></div>;
}
