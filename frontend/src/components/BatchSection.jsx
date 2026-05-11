import { useState } from 'react'
import { formatSize, formatNumber, capitalize } from '../utils/format'

const PRESETS = [
  { id:'auto',  icon:'🔮', label:'Auto',  desc:'Smart detect' },
  { id:'clean', icon:'✨', label:'Clean', desc:'Digital PDF'   },
  { id:'scan',  icon:'📠', label:'Scan',  desc:'Scanned doc'   },
  { id:'photo', icon:'📷', label:'Photo', desc:'Camera shot'   },
]

export default function BatchSection({ files, preset, setPreset, useAi, setUseAi, onReset }) {
  // Each entry: { file_id, filename, size, status:'pending'|'processing'|'done'|'error', result?, error? }
  const [queue,    setQueue]    = useState(files.map(f => ({ ...f, status: 'pending' })))
  const [running,  setRunning]  = useState(false)
  const [expanded, setExpanded] = useState(null)

  const allDone = queue.every(q => q.status === 'done' || q.status === 'error')
  const doneCount = queue.filter(q => q.status === 'done').length

  async function processAll() {
    setRunning(true)
    for (let i = 0; i < queue.length; i++) {
      if (queue[i].status === 'done') continue
      setQueue(prev => prev.map((q, idx) => idx === i ? { ...q, status: 'processing' } : q))

      try {
        const res     = await fetch('/process', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ file_id: queue[i].file_id, preset, use_ai: useAi }),
        })
        const reader  = res.body.getReader()
        const decoder = new TextDecoder()
        let buf = ''
        let finalResult = null

        while (true) {
          const { done, value } = await reader.read()
          if (done) break
          buf += decoder.decode(value, { stream: true })
          const parts = buf.split('\n\n')
          buf = parts.pop()
          for (const part of parts) {
            if (!part.startsWith('data: ')) continue
            try {
              const d = JSON.parse(part.slice(6))
              if (d.step === 'complete' && d.result) finalResult = d.result
            } catch { /* skip */ }
          }
        }

        setQueue(prev => prev.map((q, idx) =>
          idx === i ? { ...q, status: finalResult ? 'done' : 'error', result: finalResult } : q
        ))
      } catch (e) {
        setQueue(prev => prev.map((q, idx) =>
          idx === i ? { ...q, status: 'error', error: e.message } : q
        ))
      }
    }
    setRunning(false)
  }

  function downloadTxt(item) {
    if (!item.result?.full_text) return
    const blob = new Blob([item.result.full_text], { type: 'text/plain;charset=utf-8' })
    const url  = URL.createObjectURL(blob)
    const a    = document.createElement('a')
    a.href     = url
    a.download = item.filename.replace(/\.[^.]+$/, '') + '_ocr.txt'
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <section className="anim-up">
      <div className="sh">
        <h2>📦 Batch Processing</h2>
        <p>{queue.length} file(s) queued · all will use the same settings</p>
      </div>

      {/* File queue */}
      <div className="batch-list">
        {queue.map((item, i) => (
          <div key={item.file_id} className="batch-item">
            <span style={{ fontSize:'1.2rem' }}>
              {item.status === 'pending'    && '⏳'}
              {item.status === 'processing' && <span className="spin spin-sm" />}
              {item.status === 'done'       && '✅'}
              {item.status === 'error'      && '❌'}
            </span>
            <span className="batch-item-name">{item.filename}</span>
            <span className="batch-item-size">{formatSize(item.size)}</span>
            <span className={`batch-status ${item.status}`}>
              {item.status === 'pending'    && 'Pending'}
              {item.status === 'processing' && 'Processing…'}
              {item.status === 'done'       && `${formatNumber(item.result?.full_text?.length || 0)} chars`}
              {item.status === 'error'      && 'Failed'}
            </span>
          </div>
        ))}
      </div>

      {/* Settings (only shown before running) */}
      {!allDone && (
        <div className="settings-grid" style={{ marginBottom:'1.25rem' }}>
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
            {useAi && <p className="warn">⚠️ Requires GOOGLE_API_KEY in .env</p>}
          </div>
        </div>
      )}

      {/* Action button */}
      {!allDone ? (
        <button className="btn btn-primary btn-lg" onClick={processAll} disabled={running}>
          {running
            ? <><span className="spin spin-sm" /> Processing {doneCount}/{queue.length}…</>
            : <><span>🚀</span> Process All {queue.length} Files</>
          }
        </button>
      ) : (
        <div style={{ marginBottom:'1.5rem' }}>
          <p style={{ fontSize:'.82rem', color:'var(--green)', fontWeight:600, marginBottom:'1rem' }}>
            ✅ {doneCount}/{queue.length} file(s) completed
          </p>

          {/* Results per file */}
          {queue.filter(q => q.status === 'done').map(item => (
            <div key={item.file_id} className="batch-result-card">
              <div
                className="batch-result-head"
                onClick={() => setExpanded(v => v === item.file_id ? null : item.file_id)}
              >
                <div style={{ display:'flex', alignItems:'center', gap:'.65rem' }}>
                  <span>📄</span>
                  <span style={{ fontSize:'.85rem', fontWeight:600 }}>{item.filename}</span>
                  <span style={{ fontSize:'.7rem', color:'var(--txt-3)' }}>
                    {item.result?.total_pages} page(s) · {formatNumber(item.result?.full_text?.length || 0)} chars
                  </span>
                </div>
                <div style={{ display:'flex', gap:'.45rem', alignItems:'center' }}>
                  <button
                    className="btn btn-outline btn-sm"
                    onClick={e => { e.stopPropagation(); downloadTxt(item) }}
                  >⬇ TXT</button>
                  <a
                    className="btn btn-outline btn-sm"
                    href={`/download/${item.file_id}/docx`}
                    onClick={e => e.stopPropagation()}
                  >📝 DOCX</a>
                  <span style={{ color:'var(--txt-3)', fontSize:'.72rem' }}>
                    {expanded === item.file_id ? '▲' : '▼'}
                  </span>
                </div>
              </div>
              {expanded === item.file_id && (
                <div style={{ padding:'1rem' }} className="anim-in">
                  <pre className="batch-result-text">{item.result?.full_text || '—'}</pre>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      <button
        className={`btn btn-ghost btn-sm`}
        style={{ marginTop: allDone ? 0 : '1rem' }}
        onClick={onReset}
      >
        ← Back to Upload
      </button>
    </section>
  )
}
