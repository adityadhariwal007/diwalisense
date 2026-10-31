export default function PageHeader({ active }: { active: 'compare' | 'guidelines' | 'data' }) {
  return <header className="page-header">
    <a href="#home" className="page-brand font-display">DiwaliSense<span aria-hidden="true">✳</span></a>
    <nav aria-label="Main navigation">
      <a href="#compare" aria-current={active === 'compare' ? 'page' : undefined}>Compare air</a>
      <a href="#guidelines" aria-current={active === 'guidelines' ? 'page' : undefined}>What to do</a>
      <a href="#data" aria-current={active === 'data' ? 'page' : undefined}>About the data</a>
    </nav>
  </header>;
}
