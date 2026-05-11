import { useEffect, useState } from 'react'
import { formatNumber } from '../utils/format'

function timeAgo(iso) {
  const diff = Date.now() - new Date(iso).getTime()
  const m = Math.floor(diff / 60000)
  if (m < 1)   return 'just now'
  if (m < 60)  return `${m}m ago`
  const h = Math.floor(m / 60)
  if (h < 24)  return `${h}h ago`
  return new Date(iso).toLocaleDateString()
}

export default function HistorySection({ onReset }) {
  const [items,    setItems]    = useState(null)
  const [expanded, setExpanded] = useState(null)   // history id being viewed
  const [detail,   setDetail]   = useState(null)   // full text + pages for expanded item
  const [loading,  setLoading]  = useState(false)
  const [error,    setError]    = useState(null)

  useEffect(() => { loadHistory() }, [])

  async function loadHistory() {
    try {
      const r = await fetch('/history')
      setItems(await r.json())
    } catch { setError('Failed to load history.') }
  }

  async function expand(id) {
    if (expanded === id) { setExpanded(null); setDetail(null); return }
    setExpanded(id); setLoading(true); setDetail(null)
    try {
      const r = await fetch(`/history/${id}`)
      setDetail(await r.json())
    } catch { setDetail({ full_text: 'Failed to load text.' }) }
    finally  { setLoading(false) }
  }

  async function deleteItem(id, e) {
    e.stopPropagation()
    if (!confirm('Delete this history entry?')) return
    await fetch(`/history/${id}`, { method: 'DELETE' })
    setItems(prev => prev.filter(it => it.id !== id))
    if (expanded === id) { setExpanded(null); setDetail(null) }
  }

  function downloadTxt(item) {
    if (!detail?.full_text) return
    const blob = new Blob([detail.full_text], { type: 'text/plain;charset=utf-8' })
    const url  = URL.createObjectURL(blob)
    const a    = document.createElement('a')
    a.href     = url
    a.download = item.filename.replace(/\.[^.]+$/, '') + '_ocr.txt'
    a.click()
    URL.revokeObjectURL(url)
  }

  if (error) return <p className="warn">{error}</p>

  return (
    <section className="anim-up">
      <div className="sh">
        <h2>🕓 History</h2>
        <p>Past extractions saved on this device — click any item to view text</p>
      </div>

      {items === null && (
        <div style={{ display:'flex', justifyContent:'center', padding:'3rem' }}>
          <div className="spin spin-lg" />
        </div>
      )}

      {items?.length === 0 && (
        <div className="card" style={{ textAlign:'center', padding:'3rem' }}>
          <p style={{ fontSize:'2rem', marginBottom:'.75rem' }}>📭</p>
          <p style={{ color:'var(--txt-2)', fontSize:'.88rem' }}>No history yet.</p>
          <p style={{ color:'var(--txt-3)', fontSize:'.76rem', marginTop:'.3rem' }}>Process a document to see it here.</p>
          <button className="btn btn-primary btn-sm" style={{ marginTop:'1.25rem' }} onClick={onReset}>
            📄 Start Extracting
          </button>
        </div>
      )}

      {items?.length > 0 && (
        <>
          <div className="history-list">
            {items.map(item => (
              <div key={item.id}>
                <div className="history-item" onClick={() => expand(item.id)}>
                  <span className="history-icon">📄</span>
                  <div className="history-info">
                    <p className="history-name">{item.filename}</p>
                    <p className="history-meta">
                      {timeAgo(item.timestamp)} &nbsp;·&nbsp;
                      {item.total_pages} page(s) &nbsp;·&nbsp;
                      {formatNumber(item.char_count)} chars &nbsp;·&nbsp;
                      {item.preset}
                      {item.ai_corrected ? ' · AI' : ''}
                    </p>
                  </div>
                  <div className="history-actions">
                    {expanded === item.id && detail && (
                      <button
                        className="btn btn-outline btn-sm"
                        onClick={e => { e.stopPropagation(); downloadTxt(item) }}
                      >⬇ TXT</button>
                    )}
                    <button
                      className="btn btn-ghost btn-sm"
                      style={{ color:'var(--red)', fontSize:'.7rem' }}
                      onClick={e => deleteItem(item.id, e)}
                    >🗑</button>
                    <span style={{ fontSize:'.72rem', color:'var(--txt-3)' }}>
                      {expanded === item.id ? '▲' : '▼'}
                    </span>
                  </div>
                </div>

                {expanded === item.id && (
                  <div className="history-expanded anim-in">
                    {loading && <div className="spin spin-sm" style={{ margin:'.5rem auto' }} />}
                    {detail && (
                      <pre className="history-text-preview">
                        {detail.full_text || '—'}
                      </pre>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>

          <button
            className="btn btn-ghost btn-sm"
            style={{ marginTop:'1rem', color:'var(--red)' }}
            onClick={async () => {
              if (!confirm('Clear all history?')) return
              for (const it of items) await fetch(`/history/${it.id}`, { method: 'DELETE' })
              setItems([])
            }}
          >
            🗑 Clear All History
          </button>
        </>
      )}
    </section>
  )
}
