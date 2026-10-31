import { useEffect, useRef, useState } from 'react';
import { videoOpacity } from './video-loop';
import ComparisonPage, { type LocationChoice } from './ComparisonPage';
import GuidelinesPage, { AboutDataPage } from './GuidelinesPage';

type Panel = 'approach' | 'sources' | 'team';
const currentPage = () => window.location.hash.slice(1);

const content: Record<Panel, { title: string; intro: string; details: [string, string][] }> = {
  approach: {
    title: 'Two models. One clearer picture.',
    intro: 'Separate the everyday background from the extra pollution around Diwali.',
    details: [
      ['Background pollution', 'Recent PM2.5, wind and weather help estimate the usual pollution level.'],
      ['The Diwali increase', 'The 2024 event helps estimate an additional increase. One training Diwali is limited evidence; this does not prove that crackers alone caused it.'],
      ['A local view', 'The working build forecasts monitoring stations with uncertainty. Ward estimates remain a planned extension.'],
    ],
  },
  sources: {
    title: 'Grounded in environmental data.',
    intro: 'The working model uses the repository’s audited Delhi 2024–2025 data package.',
    details: [
      ['Air & weather', 'OpenCity station observations and historical reanalysis weather. Reporting latency and timestamp assumptions remain limitations.'],
      ['Earlier history', '2017–2020 Kaggle records are staged but excluded until station mapping and timezone checks are complete.'],
      ['Planned inputs', 'Regional fires, roads, ban context and ward estimates are not part of this working model yet.'],
    ],
  },
  team: {
    title: 'Built by Clauders.',
    intro: 'Aditya, Maanvik, Palakshi and Manveer. A student team at RootAccess.',
    details: [
      ['Our focus', 'Make local pollution forecasts understandable, including what we do not know.'],
      ['Current stage', 'A trained historical model, measured holdout comparisons, API and interactive replay dashboard.'],
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
  const [panel, setPanel] = useState<Panel>('approach');
  const [menuOpen, setMenuOpen] = useState(false);
  const dialog = useRef<HTMLDialogElement>(null);
  const [page, setPage] = useState(currentPage);
  const [chosenLocation, setChosenLocation] = useState<LocationChoice | null>(null);
  useEffect(() => {
    const update = () => { setPage(currentPage()); window.scrollTo(0, 0); };
    window.addEventListener('hashchange', update);
    return () => window.removeEventListener('hashchange', update);
  }, []);
  const open = (next: Panel | 'forecast' | 'guidelines') => {
    setMenuOpen(false);
    if (next === 'forecast' || next === 'guidelines') { window.location.hash = next === 'forecast' ? 'compare' : 'guidelines'; return; }
    setPanel(next); dialog.current?.showModal();
  };
  if (page === 'compare') return <ComparisonPage location={chosenLocation} onLocationChange={setChosenLocation} />;
  if (page === 'guidelines') return <GuidelinesPage />;
  if (page === 'data') return <AboutDataPage />;

  return <main id="home" className="hero-shell relative isolate min-h-screen w-full overflow-hidden bg-background text-black">
    <BackgroundVideo />
    <nav className="relative z-10 mx-auto flex w-full max-w-7xl items-center justify-between px-8 py-6" aria-label="Main navigation">
      <a href="#home" className="font-display text-3xl tracking-tight" aria-label="DiwaliSense home">DiwaliSense<span className="brand-spark" aria-hidden="true">✳</span></a>
      <div className="desktop-nav flex items-center gap-8 text-sm">
        <a href="#home" aria-current="page">Home</a>
        <button onClick={() => open('approach')}>Our approach</button>
        <button onClick={() => open('guidelines')}>What to do</button>
        <button onClick={() => open('team')}>The team</button>
      </div>
      <button className="nav-cta rounded-full bg-black px-6 py-2.5 text-sm text-white transition-transform hover:scale-[1.03]" onClick={() => open('forecast')}>Explore forecast</button>
      <button className="mobile-toggle" aria-expanded={menuOpen} aria-controls="mobile-navigation" onClick={() => setMenuOpen(!menuOpen)}>{menuOpen ? 'Close' : 'Menu'}</button>
    </nav>
    {menuOpen && <div id="mobile-navigation" className="mobile-navigation">
      <a href="#home" onClick={() => setMenuOpen(false)}>Home</a>
      <button onClick={() => open('approach')}>Our approach</button>
      <button onClick={() => open('guidelines')}>What to do</button>
      <button onClick={() => open('team')}>The team</button>
      <button onClick={() => open('forecast')}>Explore forecast</button>
    </div>}
    <section className="hero-content relative z-10 flex flex-col items-center justify-center px-6 pb-40 text-center" aria-labelledby="hero-title">
      <h1 id="hero-title" className="font-display animate-fade-rise max-w-7xl text-5xl font-normal sm:text-7xl md:text-8xl">
        Understanding the air<br className="desktop-break" /> before, during and after <em className="text-muted">Diwali.</em>
      </h1>
      <p className="animate-fade-rise-delay mt-8 max-w-2xl text-base leading-relaxed text-muted sm:text-lg">
        Local pollution forecasts, with the uncertainty in plain sight.
      </p>
      <div className="animate-fade-rise-delay-2 mt-12">
        <button className="hero-cta rounded-full bg-black px-14 py-5 text-base text-white transition-transform hover:scale-[1.03]" onClick={() => open('forecast')}>Explore forecast <span aria-hidden="true">↗</span></button>
      </div>
    </section>
    <footer className="hero-footer relative z-10 mx-auto flex w-full max-w-7xl justify-between gap-5 px-8">
      <p>Delhi air comparison · 2025</p>
      <a href="#data">About the data</a>
    </footer>
    <dialog ref={dialog} className="info-dialog" aria-labelledby="dialog-title" onClick={event => { if (event.target === dialog.current) dialog.current.close(); }}>
      <button className="dialog-close" onClick={() => dialog.current?.close()} aria-label="Close panel">×</button>
      <p className="dialog-kicker">DiwaliSense / {panel === 'approach' ? 'Our approach' : panel === 'sources' ? 'Data sources' : 'Team Clauders'}</p>
      <h2 id="dialog-title" className="font-display">{content[panel].title}</h2>
      <p className="dialog-intro">{content[panel].intro}</p>
      <dl>{content[panel].details.map(([title, description]) => <div key={title}><dt>{title}</dt><dd>{description}</dd></div>)}</dl>
      <button className="dialog-return" onClick={() => dialog.current?.close()}>Back to the view</button>
    </dialog>
  </main>;
}
