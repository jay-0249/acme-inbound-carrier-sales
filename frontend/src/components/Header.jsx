import './Header.css'

export default function Header() {
  return (
    <header className="header">
      <div className="header-inner">
        <div className="header-left">
          <span className="header-brand">Acme Carrier Sales</span>
          <span className="header-scope">Last 14 days</span>
        </div>
        <div className="status-pill">
          <span className="status-dot" aria-hidden="true" />
          <span>Agent active</span>
          <span className="status-sep" aria-hidden="true">·</span>
          <span>24 / 7</span>
        </div>
      </div>
    </header>
  )
}
