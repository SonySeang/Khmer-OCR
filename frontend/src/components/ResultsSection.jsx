import { useState } from 'react'
import { formatNumber, capitalize, mode } from '../utils/format'

export default function ResultsSection({ result, onReset }) {
  const [tab,    setTab]    = useState('corrected')
  const [copied, setCopied] = useState(false)
  const [open,   setOpen]   = useState(false)

  const docType    = result.pages?.length ? capitalize(mode(result.pages.map(p => p.quality?.recommended_preset || '—'))) : '—'
  const totalFixed = result.pages?.reduce((s, p) => s + (p.lines_removed || 0), 0) ?? 0

  const displayText = tab === 'corrected'
    ? result.full_text
    : result.pages?.map(p => `--- Page ${p.page} ---\n${p.text}`).join('\n\n') || result.full_text

  async function copy() {
    try { await navigator.clipboard.writeText(result.full_text) }
    catch {
      const t = document.createElement('textarea')
      t.value = result.full_text
      document.body.appendChild(t); t.select(); document.execCommand('copy'); document.body.removeChild(t)
    }
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <section className="anim-up">
      <div className="sh">
        <h2>Extracted Text</h2>
        <p>{result.filename} &nbsp;·&nbsp; {result.total_pages} page(s)</p>
      </div>

      {/* Stats */}
      <div className="stats">
        {[
          { v: result.total_pages,                   l: 'Pages'       },
          { v: formatNumber(result.full_text.length), l: 'Characters'  },
          { v: docType,                               l: 'Doc Type'    },
          { v: totalFixed,                            l: 'Lines Fixed' },
        ].map(s => (
          <div key={s.l} className="card stat-card">
            <span className="stat-val">{s.v}</span>
            <span className="stat-lbl">{s.l}</span>
          </div>
        ))}
      </div>

      {/* Text output card */}
      <div className="card" style={{ marginBottom:'1rem' }}>
        <div className="result-bar">
          <div className="tabs">
            <button className={`tab${tab === 'corrected' ? ' active' : ''}`} onClick={() => setTab('corrected')}>Corrected</button>
            <button className={`tab${tab === 'raw'       ? ' active' : ''}`} onClick={() => setTab('raw')}>Raw OCR</button>
          </div>
          <div className="result-actions">
            <button className="btn btn-ghost btn-sm" onClick={copy}>
              {copied ? '✅ Copied!' : '📋 Copy'}
            </button>
            <a className="btn btn-outline btn-sm" href={`/download/${result.file_id}`}>
              ⬇️ Download .txt
            </a>
          </div>
        </div>

        <div className="text-out">
          <pre className="khmer">{displayText || '—'}</pre>
        </div>
      </div>

      {/* Quality accordion */}
      <div className="card" style={{ padding:0, overflow:'hidden', marginBottom:'1.5rem' }}>
        <button className="accordion-btn" onClick={() => setOpen(!open)}>
          <span>📊 Per-Page Quality Details</span>
          <span className={`accordion-chevron${open ? ' open' : ''}`}>▼</span>
        </button>
        {open && (
          <div className="quality-grid anim-in">
            {result.pages?.map(p => (
              <div key={p.page} className="card-inner quality-card">
                <h4>📄 Page {p.page}</h4>
                {[
                  ['Type',        capitalize(p.quality?.recommended_preset)],
                  ['Noise',       p.quality?.noise_level ?? '—'],
                  ['Contrast',    p.quality?.contrast ?? '—'],
                  ['White %',     `${p.quality?.white_ratio ?? '—'}%`],
                  ['Lines Fixed', p.lines_removed || 0],
                  ['Characters',  formatNumber(p.char_count || 0)],
                ].map(([k, v]) => (
                  <div key={k} className="q-row"><span>{k}</span><span>{v}</span></div>
                ))}
              </div>
            ))}
          </div>
        )}
      </div>

      <button className="btn btn-primary btn-lg" onClick={onReset}>
        📄 Process Another Document
      </button>
    </section>
  )
}
