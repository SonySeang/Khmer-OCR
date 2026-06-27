export default function Header({ view, setView, V }) {
  return (
    <header className="header">
      <div className="header-inner">
        <a href="/" className="logo" onClick={e => { e.preventDefault(); setView(V.UPLOAD) }}>
          <div className="logo-mark">ក</div>
          <div>
            <div className="logo-name">Khmer OCR</div>
            <div className="logo-sub">អក្សរខ្មែរ Text Extractor</div>
          </div>
        </a>

        <nav className="nav-links">
          <button
            className={`nav-link${view === V.UPLOAD || view === V.SETTINGS || view === V.PROGRESS || view === V.RESULTS ? ' active' : ''}`}
            onClick={() => setView(V.UPLOAD)}
          >
            📄 Extract
          </button>
          <button
            className={`nav-link${view === V.BATCH ? ' active' : ''}`}
            onClick={() => setView(V.BATCH)}
          >
            📦 Batch
          </button>
          <button
            className={`nav-link${view === V.HISTORY ? ' active' : ''}`}
            onClick={() => setView(V.HISTORY)}
          >
            🕓 History
          </button>
        </nav>

        <div className="pill">
          <span className="dot" />
          Ready
        </div>
      </div>
    </header>
  )
}
