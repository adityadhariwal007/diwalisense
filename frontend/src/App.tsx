import { useEffect, useRef, useState } from 'react';
import { videoOpacity } from './video-loop';

type Panel = 'forecast' | 'approach' | 'sources' | 'team';

const content: Record<Panel, { title: string; intro: string; details: [string, string][] }> = {
  forecast: {
    title: 'A clearer forecast is next.',
    intro: 'Our Delhi-NCR forecast is under development. No validated predictions are available yet.',
    details: [
      ['Before, during, after', 'The planned forecast follows pollution across the Diwali period.'],
      ['An estimate, with a range', 'Areas without sensors will show estimates, with uncertainty clearly labelled.'],
      ['Our next milestone', 'Train a baseline on real data and compare it with a simple persistence forecast.'],
    ],
  },
  approach: {
    title: 'Two models. One clearer picture.',
    intro: 'Separate the everyday background from the extra pollution around Diwali.',
    details: [
      ['Background pollution', 'Recent PM2.5, wind and weather help estimate the usual pollution level.'],
      ['The Diwali increase', 'Past festival periods help estimate an additional increase. This does not prove that crackers alone caused it.'],
      ['A local view', 'Combine the forecasts, estimate neighborhood differences and show the uncertainty.'],
    ],
  },
  sources: {
    title: 'Grounded in environmental data.',
    intro: 'Planned inputs for our Delhi-NCR pilot. Access and historical coverage still need verification.',
    details: [
      ['Air & weather', 'OpenAQ / CPCB pollution records and Open-Meteo weather.'],
      ['Regional context', 'NASA FIRMS fire detections and OpenStreetMap roads and land use.'],
      ['Festival context', 'A manually checked Diwali and cracker-ban calendar.'],
    ],
  },
  team: {
    title: 'Built by Clauders.',
    intro: 'Aditya, Maanvik, Palakshi and Manveer. A student team at RootAccess.',
    details: [
      ['Our focus', 'Make local pollution forecasts understandable, including what we do not know.'],
      ['Current stage', 'Architecture and code scaffold. Model training and forecast validation are still ahead.'],
    ],
  },
};

function BackgroundVideo() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [paused, setPaused] = useState(false);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;
    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
    let frame = 0;
    let restart: ReturnType<typeof setTimeout> | undefined;
    let disposed = false;
    let running = false;
    const play = () => {
      if (!disposed) void video.play().catch(() => { if (!disposed) setPaused(true); });
    };
    const tick = () => {
      video.style.opacity = String(videoOpacity(video.currentTime, video.duration));
      frame = requestAnimationFrame(tick);
    };
    const sync = () => {
      running = !paused && !reducedMotion.matches;
      clearTimeout(restart);
      cancelAnimationFrame(frame);
      if (!running) video.pause();
      else { frame = requestAnimationFrame(tick); play(); }
    };
    const ended = () => {
      video.style.opacity = '0';
      restart = setTimeout(() => {
        if (!disposed && running) { video.currentTime = 0; play(); }
      }, 100);
    };
    video.addEventListener('ended', ended);
    reducedMotion.addEventListener('change', sync);
    sync();
    return () => {
      disposed = true;
      video.pause();
      cancelAnimationFrame(frame);
      clearTimeout(restart);
      video.removeEventListener('ended', ended);
      reducedMotion.removeEventListener('change', sync);
    };
  }, [paused]);

  return <>
    <div className="video-stage absolute z-0" aria-hidden="true">
      <video ref={videoRef} muted playsInline preload="auto" poster="/hero-poster.jpg"
        className="h-full w-full object-cover opacity-0" onError={() => setFailed(true)}>
        <source src="/hero.mp4" type="video/mp4" />
      </video>
      <div className="pointer-events-none absolute inset-0 bg-gradient-to-b from-background via-transparent to-background" />
      <div className="video-wash pointer-events-none absolute inset-0" />
    </div>
    {!failed && <button className="motion-control" onClick={() => setPaused(!paused)}
      aria-label={paused ? 'Play background video' : 'Pause background video'} aria-pressed={paused}>
      {paused ? <svg viewBox="0 0 16 16" aria-hidden="true"><path d="m5 3 8 5-8 5Z" fill="currentColor" /></svg>
        : <svg viewBox="0 0 16 16" aria-hidden="true"><path d="M5 3v10M11 3v10" stroke="currentColor" strokeWidth="2" /></svg>}
    </button>}
  </>;
}

export default function App() {
  const [panel, setPanel] = useState<Panel>('forecast');
  const [menuOpen, setMenuOpen] = useState(false);
  const dialog = useRef<HTMLDialogElement>(null);
  const open = (next: Panel) => { setPanel(next); setMenuOpen(false); dialog.current?.showModal(); };

  return <main id="home" className="hero-shell relative isolate min-h-screen w-full overflow-hidden bg-background text-black">
    <BackgroundVideo />
    <nav className="relative z-10 mx-auto flex w-full max-w-7xl items-center justify-between px-8 py-6" aria-label="Main navigation">
      <a href="#home" className="font-display text-3xl tracking-tight" aria-label="DiwaliSense home">DiwaliSense<span className="brand-spark" aria-hidden="true">✳</span></a>
      <div className="desktop-nav flex items-center gap-8 text-sm">
        <a href="#home" aria-current="page">Home</a>
        <button onClick={() => open('approach')}>Our approach</button>
        <button onClick={() => open('sources')}>Data sources</button>
        <button onClick={() => open('team')}>The team</button>
      </div>
      <button className="nav-cta rounded-full bg-black px-6 py-2.5 text-sm text-white transition-transform hover:scale-[1.03]" onClick={() => open('forecast')}>Explore forecast</button>
      <button className="mobile-toggle" aria-expanded={menuOpen} aria-controls="mobile-navigation" onClick={() => setMenuOpen(!menuOpen)}>{menuOpen ? 'Close' : 'Menu'}</button>
    </nav>
    {menuOpen && <div id="mobile-navigation" className="mobile-navigation">
      <a href="#home" onClick={() => setMenuOpen(false)}>Home</a>
      <button onClick={() => open('approach')}>Our approach</button>
      <button onClick={() => open('sources')}>Data sources</button>
      <button onClick={() => open('team')}>The team</button>
      <button onClick={() => open('forecast')}>Explore forecast</button>
    </div>}
    <section className="hero-content relative z-10 flex flex-col items-center justify-center px-6 pb-40 text-center" aria-labelledby="hero-title">
      <div className="pilot-note animate-fade-rise"><span aria-hidden="true" /> A Delhi-NCR pilot, by Clauders</div>
      <h1 id="hero-title" className="font-display animate-fade-rise max-w-7xl text-5xl font-normal sm:text-7xl md:text-8xl">
        A little clarity<br />in the <em className="text-muted">Diwali haze.</em>
      </h1>
      <p className="animate-fade-rise-delay mt-8 max-w-2xl text-base leading-relaxed text-muted sm:text-lg">
        Understanding the air before, during and after Diwali.<br className="desktop-break" /> Local pollution forecasts, with the uncertainty in plain sight.
      </p>
      <div className="animate-fade-rise-delay-2 mt-12">
        <button className="hero-cta rounded-full bg-black px-14 py-5 text-base text-white transition-transform hover:scale-[1.03]" onClick={() => open('forecast')}>Explore forecast <span aria-hidden="true">↗</span></button>
        <p className="prototype-note">Student prototype. Forecasts under development.</p>
      </div>
    </section>
    <footer className="hero-footer relative z-10 mx-auto flex w-full max-w-7xl justify-between gap-5 px-8">
      <p>For the places we call home.</p>
      <p>Neighborhood estimates. Never sensor measurements.</p>
    </footer>
    <dialog ref={dialog} className="info-dialog" aria-labelledby="dialog-title" onClick={event => { if (event.target === dialog.current) dialog.current.close(); }}>
      <button className="dialog-close" onClick={() => dialog.current?.close()} aria-label="Close panel">×</button>
      <p className="dialog-kicker">DiwaliSense / {panel === 'forecast' ? 'Prototype' : panel === 'approach' ? 'Our approach' : panel === 'sources' ? 'Data sources' : 'Team Clauders'}</p>
      <h2 id="dialog-title" className="font-display">{content[panel].title}</h2>
      <p className="dialog-intro">{content[panel].intro}</p>
      <dl>{content[panel].details.map(([title, description]) => <div key={title}><dt>{title}</dt><dd>{description}</dd></div>)}</dl>
      <button className="dialog-return" onClick={() => dialog.current?.close()}>Back to the view</button>
    </dialog>
  </main>;
}
