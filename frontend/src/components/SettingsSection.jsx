import { formatSize } from '../utils/format'

const PRESETS = [
  { id:'auto',  icon:'🔮', label:'Auto',  desc:'Smart detect' },
  { id:'clean', icon:'✨', label:'Clean', desc:'Digital PDF'  },
  { id:'scan',  icon:'📠', label:'Scan',  desc:'Scanned doc'  },
  { id:'photo', icon:'📷', label:'Photo', desc:'Camera shot'  },
]

export default function SettingsSection({ filename, fileSize, preset, setPreset, useAi, setUseAi, onRemove, onProcess }) {
  return (
    <section className="anim-up">

      {/* File chip */}
      <div className="file-chip">
        <div className="file-chip-left">
          <span className="file-chip-icon">📄</span>
          <div>
            <p className="file-chip-name">{filename}</p>
            <p className="file-chip-size">{formatSize(fileSize)}</p>
          </div>
        </div>
        <button className="btn btn-ghost btn-sm" onClick={onRemove}>✕ Remove</button>
      </div>

      <div className="sh">
        <h2>Processing Settings</h2>
        <p>Configure the OCR pipeline for your document type</p>
      </div>

      <div className="settings-grid">
        {/* Preset */}
        <div className="card">
          <p className="label-cap">Preprocessing Mode</p>
          <div className="presets">
            {PRESETS.map(p => (
              <button key={p.id} className={`preset${preset === p.id ? ' active' : ''}`} onClick={() => setPreset(p.id)}>
                <span className="preset-icon">{p.icon}</span>
                <span className="preset-name">{p.label}</span>
                <span className="preset-desc">{p.desc}</span>
              </button>
            ))}
          </div>
        </div>

        {/* AI toggle */}
        <div className="card">
          <p className="label-cap">AI Correction</p>
          <div className="toggle-wrap">
            <label className="toggle">
              <input type="checkbox" checked={useAi} onChange={e => setUseAi(e.target.checked)} />
              <span className="track" />
            </label>
            <div className="toggle-label">
              <p>Google Gemini AI</p>
              <p>Fix complex OCR errors with AI</p>
            </div>
          </div>
          {useAi && <p className="warn">⚠️ Requires GOOGLE_API_KEY in your .env file</p>}
        </div>
      </div>

      <button className="btn btn-primary btn-lg" onClick={onProcess}>
        <span>🚀</span> Start Processing
      </button>
    </section>
  )
}
