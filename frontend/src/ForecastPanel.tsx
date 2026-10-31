import { useEffect, useState } from 'react';

const API = import.meta.env.DEV ? '/api' : '';
type Station = { id: string; name: string; availability: Record<string, number[]> };
type Point = { local_time: string; time: string; issue_time: string; p10: number; p50: number; p90: number; observed: number; baseline: number; diwali_adjustment: number; persistence: number };
type Forecast = Point & { station_name: string; series: Point[]; range_note: string; series_note: string; advice: string };
type Score = { n: number; mae: number; rmse: number };
type Evaluation = { model: Score; baseline_only: Score; persistence: Score; interval_coverage: number };
type Report = { all_test: Evaluation; diwali_test: Evaluation; leave_one_station_out: Record<string, Evaluation>; independent_training_diwalis: number };
type Priority = { station_name: string; p10: number; p50: number; p90: number };

async function request<T>(path: string, signal: AbortSignal): Promise<T> {
  const response = await fetch(`${API}${path}`, { signal });
  const body = await response.json();
  if (!response.ok) throw new Error(typeof body.detail === 'string' ? body.detail : 'Unable to load model output. Check the API server and try again.');
  return body as T;
}
const timeLabel = (value: string) => new Date(value).toLocaleString('en-IN', { timeZone: 'Asia/Kolkata', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit', hour12: false });

function ForecastChart({ points }: { points: Point[] }) {
  const max = Math.max(1, ...points.flatMap(point => [point.p90, point.observed]));
  const x = (point: Point) => 48 + (Date.parse(point.time) - Date.parse(points[0].time)) / Math.max(1, Date.parse(points[points.length - 1].time) - Date.parse(points[0].time)) * 604;
  const y = (value: number) => 200 - value / max * 170;
  const line = (field: 'p50' | 'observed') => points.map(point => `${x(point)},${y(point[field])}`).join(' ');
  const band = [...points.map(point => `${x(point)},${y(point.p90)}`), ...points.slice().reverse().map(point => `${x(point)},${y(point.p10)}`)].join(' ');
  return <figure className="forecast-chart">
    <figcaption>Pollution around the selected time <span>µg/m³</span></figcaption>
    <svg viewBox="0 0 680 240" role="img" aria-label="Historical PM2.5: model median, uncertainty range and observed pollution. Exact values are available in the table below.">
      {[0, 0.5, 1].map(fraction => <g key={fraction}><line x1="48" x2="652" y1={y(max * fraction)} y2={y(max * fraction)} stroke="#e0e5df" /><text x="38" y={y(max * fraction) + 4} textAnchor="end" fill="#647067" fontSize="11">{Math.round(max * fraction)}</text></g>)}
      <polygon points={band} fill="#dae7dc" />
      <polyline points={line('observed')} fill="none" stroke="#a07451" strokeWidth="2" strokeDasharray="5 5" />
      <polyline points={line('p50')} fill="none" stroke="#31573a" strokeWidth="3" />
      {[points[0], points[points.length - 1]].map((point, index) => <text key={index} x={x(point)} y="228" textAnchor={index ? 'end' : 'start'} fontSize="11" fill="#647067">{timeLabel(point.local_time)}</text>)}
    </svg>
    <div className="chart-legend"><span>━━ Model median</span><span>▧ Model range</span><span>┄ Observed after issue time</span></div>
  </figure>;
}

export default function ForecastPanel() {
  const [stations, setStations] = useState<Station[]>([]);
  const [station, setStation] = useState('');
  const [date, setDate] = useState('2025-10-20');
  const [hour, setHour] = useState('23');
  const [view, setView] = useState('resident');
  const [report, setReport] = useState<Report | null>(null);
  const [forecast, setForecast] = useState<Forecast | null>(null);
  const [priorities, setPriorities] = useState<Priority[]>([]);
  const [missingCount, setMissingCount] = useState(0);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [retry, setRetry] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    Promise.all([request<{ stations: Station[] }>('/stations', controller.signal), request<Report>('/metrics', controller.signal)])
      .then(([data, metrics]) => {
        setStations(data.stations); setReport(metrics);
        setStation(current => current || data.stations.find(item => item.id === 'site_5024')?.id || data.stations[0]?.id || '');
      }).catch(reason => { if (reason.name !== 'AbortError') { setError('Start the Python API on port 8000, then retry. ' + reason.message); setLoading(false); } });
    return () => controller.abort();
  }, [retry]);

  const availableHours = stations.find(item => item.id === station)?.availability[date] || [];
  useEffect(() => {
    if (availableHours.length && !availableHours.includes(Number(hour))) setHour(String(availableHours[availableHours.length - 1]));
  }, [station, date, stations, hour]);

  useEffect(() => {
    if (!station) return;
    const controller = new AbortController();
    setLoading(true); setError(''); setForecast(null); setPriorities([]);
    const query = `station=${encodeURIComponent(station)}&date=${date}&hour=${hour}`;
    Promise.all([
      request<Forecast>(`/forecast?${query}`, controller.signal),
      view === 'officer' ? request<{ priorities: Priority[]; missing_stations: string[] }>(`/priorities?date=${date}&hour=${hour}`, controller.signal) : Promise.resolve(null),
    ]).then(([data, priorityData]) => { setForecast(data); setPriorities(priorityData?.priorities || []); setMissingCount(priorityData?.missing_stations.length || 0); })
      .catch(reason => { if (reason.name !== 'AbortError') setError(reason.message); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [station, date, hour, view, retry]);

  return <div className="forecast-workspace">
    <p className="dialog-kicker">Delhi / historical replay / 2025 holdout</p>
    <h2 id="dialog-title" className="font-display">See the air ahead.</h2>
    <p className="forecast-intro">A working six-hour-ahead model, replayed on unseen 2025 observations. These are historical estimates, not live conditions.</p>
    <div className="forecast-controls">
      <label>Monitoring station<select value={station} onChange={event => setStation(event.target.value)} disabled={!stations.length}>{stations.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
      <label>Replay date<input type="date" min="2025-01-01" max="2025-12-31" value={date} onChange={event => { if (event.target.value) setDate(event.target.value); }} /></label>
      <label>Target hour (IST)<select value={hour} onChange={event => setHour(event.target.value)}>{['5', '11', '17', '23'].map(value => <option key={value} value={value} disabled={!availableHours.includes(Number(value))}>{value.padStart(2, '0')}:30</option>)}</select></label>
      <label>View<select value={view} onChange={event => setView(event.target.value)}><option value="resident">Resident</option><option value="officer">Officer</option></select></label>
    </div>
    <div className="phase-controls" aria-label="Diwali replay shortcuts">{[['Before Diwali', '2025-10-19'], ['Diwali', '2025-10-20'], ['After Diwali', '2025-10-21']].map(([label, value]) => <button key={value} aria-pressed={date === value} onClick={() => setDate(value)}>{label}</button>)}</div>
    <div aria-busy={loading} aria-live="polite">
      {loading && <p className="forecast-status" role="status">Running the model…</p>}
      {error && <div className="forecast-error" role="alert"><p>{error}</p><button onClick={() => setRetry(value => value + 1)}>Try again</button></div>}
      {!loading && forecast && <>
        <div className="forecast-reading"><div><span>Predicted PM2.5</span><strong>{forecast.p50.toFixed(1)} <small>µg/m³</small></strong><p>Model range: {forecast.p10.toFixed(1)}–{forecast.p90.toFixed(1)} µg/m³</p></div><div className="forecast-components"><p>Background <b>{forecast.baseline.toFixed(1)}</b></p><p>Diwali adjustment <b>{forecast.diwali_adjustment > 0 ? '+' : ''}{forecast.diwali_adjustment.toFixed(1)}</b></p><p>Observed later <b>{forecast.observed.toFixed(1)}</b></p></div></div>
        <p className="forecast-caption">{forecast.station_name} · target {timeLabel(forecast.local_time)} IST · issue {timeLabel(forecast.issue_time)} IST</p>
        <ForecastChart points={forecast.series} />
        <p className="forecast-caption">{forecast.series_note} {forecast.range_note}</p>
        {view === 'officer' && <section className="priority-section"><h3>Station-area review order</h3><p>Higher model estimates first. These are station areas, not ward estimates. Missing stations: {missingCount}.</p><div className="table-scroll"><table><thead><tr><th>Station</th><th>Median</th><th>Model range</th></tr></thead><tbody>{priorities.map(item => <tr key={item.station_name}><td>{item.station_name}</td><td>{item.p50.toFixed(1)}</td><td>{item.p10.toFixed(1)}–{item.p90.toFixed(1)}</td></tr>)}</tbody></table></div></section>}
        <details><summary>Exact replay values</summary><div className="table-scroll"><table><thead><tr><th>Time (IST)</th><th>P10</th><th>P50</th><th>P90</th><th>Observed</th></tr></thead><tbody>{forecast.series.map(point => <tr key={point.time}><td>{timeLabel(point.local_time)}</td><td>{point.p10}</td><td>{point.p50}</td><td>{point.p90}</td><td>{point.observed}</td></tr>)}</tbody></table></div></details>
        <p className="forecast-caption">{forecast.advice} The Diwali adjustment is an event-associated residual, not proven cracker pollution.</p>
      </>}
    </div>
    {report && <section className="model-validation"><h3>Measured, not promised.</h3><p>Train: Jan–Nov 2024. Interval calibration: Dec 2024. Test: 2025. All errors in µg/m³.</p><div className="table-scroll"><table><thead><tr><th>2025 evaluation</th><th>Model MAE</th><th>Persistence MAE</th><th>Model RMSE</th><th>Persistence RMSE</th></tr></thead><tbody>{[['All test times', report.all_test], ['Diwali period', report.diwali_test]].map(([label, result]) => { const score = result as Evaluation; return <tr key={label as string}><td>{label as string} ({score.model.n} rows)</td><td>{score.model.mae}</td><td>{score.persistence.mae}</td><td>{score.model.rmse}</td><td>{score.persistence.rmse}</td></tr>; })}</tbody></table></div><p>Overall interval coverage: {(report.all_test.interval_coverage * 100).toFixed(1)}%. Diwali-period coverage: {(report.diwali_test.interval_coverage * 100).toFixed(1)}% — the event range is not reliable yet. {Object.keys(report.leave_one_station_out).length} station holdouts measured.</p><p>Diwali baseline-only MAE: {report.diwali_test.baseline_only.mae}. Combined-model MAE: {report.diwali_test.model.mae}. The burst model does not consistently improve the baseline yet.</p><p>Only {report.independent_training_diwalis} independent training Diwali. Station holdout uses prior local sensor readings; it does not validate areas without sensors. Hourly PM2.5 is not a full AQI.</p></section>}
  </div>;
}
