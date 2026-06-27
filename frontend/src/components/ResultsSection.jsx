import { useState, useRef, useMemo } from 'react'
import { formatNumber, capitalize, mode } from '../utils/format'

// English words that legitimately appear in Khmer documents — do not flag these
const KNOWN_ENGLISH = new Set([
  'STEM','ChatGPT','Gemini','Claude','AI','Al','Designer','Media','Centre',
  'Excellence','KAPE','NGO','UNESCO','UNICEF','ADB','GDP','ASEAN','IMF',
  'IFC','NBC','CMA','MFI','EdTech','JOTA','JOTI','MSME','A','B','C','D',
])

function wordClass(chunk, wordConf) {
  const clean = chunk.replace(/[។,.!?:;()'"""«»[\]]/g, '').trim()
  if (!clean || clean.length < 2) return null
  if (KNOWN_ENGLISH.has(clean) || KNOWN_ENGLISH.has(clean.toUpperCase())) return null

  const khmer  = (clean.match(/[ក-៿]/g) || []).length
  const latin  = (clean.match(/[a-zA-Z]/g) || []).length
  const digits = (clean.match(/[0-9]/g)    || []).length
  const total  = clean.length

  // Pure Latin word in Khmer context = OCR error (e.g. "om", "wood", "MM")
  // Require ≥2 Latin chars so a single stray char doesn't trigger
  if (khmer === 0 && digits === 0 && latin >= 2) return 'mark-red'

  // Mixed Khmer+Latin: only flag when Latin makes up ≥25% of the token.
  // A single substituted char in a long Khmer word (e.g. 1/15 chars) would be ~7% — ignored.
  // A genuinely mixed token like "A​ble​ក" would be ~50% — flagged.
  if (khmer > 0 && latin > 0 && latin / total >= 0.25) return 'mark-yellow'

  // Special ASCII artifact inside Khmer token
  if (/[$@#\\|]/.test(clean)) return 'mark-yellow'

  // Two consecutive Khmer dependent vowels = impossible in valid Khmer → OCR doubled a vowel
  // e.g. "ួូ" in "តម្រួូវការ" (should be "តម្រូវការ")
  if (/[ា-ៅ]{2}/.test(clean)) return 'mark-yellow'

  // Pure Khmer: flag low-confidence words (matches the < 45 threshold in _process_page)
  const conf = wordConf[clean.toLowerCase()]
  if (conf !== undefined && conf < 40) return 'mark-yellow'

  return null
}

function HighlightedText({ text, wordConf, onWordClick }) {
  return (
    <div className="text-out khmer highlight-view">
      {text.split('\n').map((line, li) => (
        <p key={li} className="hl-line">
          {line.split(/(\s+)/).map((chunk, ci) => {
            if (!chunk.trim()) return <span key={ci}>{chunk}</span>
            const cls = wordClass(chunk, wordConf)
            if (!cls) return <span key={ci}>{chunk}</span>
            const conf = wordConf[chunk.toLowerCase().replace(/[។,.!?:;()'"""]/g, '')]
            const tip = conf !== undefined ? `${conf}% — click to AI correct` : 'OCR error — click to AI correct'
            return (
              <mark
                key={ci}
                className={cls}
                title={tip}
                style={{ cursor: 'pointer' }}
                onClick={() => onWordClick(chunk)}
              >{chunk}</mark>
            )
          })}
        </p>
      ))}
    </div>
  )
}

function ConfBadge({ score }) {
  const pct = Math.round((score || 0) * 100)
  const cls = score >= 0.8 ? 'badge-green' : score >= 0.5 ? 'badge-yellow' : 'badge-red'
  return <span className={`badge ${cls}`}>{pct}% confidence</span>
}

export default function ResultsSection({ result, onReset }) {
  const [tab,        setTab]        = useState('corrected')
  const [copied,     setCopied]     = useState(false)
  const [open,       setOpen]       = useState(false)
  const [editedText, setEditedText] = useState(result.full_text)
  const [isEdited,   setIsEdited]   = useState(false)

  // Inline AI correction state
  const [correcting,   setCorrecting]   = useState(false)
  const [corrections,  setCorrections]  = useState(null)  // [{original,corrected,reason}]
  const [corrErr,      setCorrErr]      = useState(null)
  const [savedDict,    setSavedDict]    = useState(false)

  // Thumbnail modal
  const [thumbModal, setThumbModal] = useState(null)

  // Dictionary panel
  const [showDict,    setShowDict]    = useState(false)
  const [dictEntries, setDictEntries] = useState(null)
  const [dictLoading, setDictLoading] = useState(false)

  const textareaRef = useRef(null)

  // Aggregate word confidences across all pages (keep lowest per word)
  const wordConf = useMemo(() => {
    const merged = {}
    for (const page of result.pages || []) {
      for (const [word, conf] of Object.entries(page.word_confidences || {})) {
        if (!(word in merged) || conf < merged[word]) merged[word] = conf
      }
    }
    return merged
  }, [result.pages])

  const docType    = result.pages?.length ? capitalize(mode(result.pages.map(p => p.quality?.recommended_preset || '—'))) : '—'
  const totalFixed = result.pages?.reduce((s, p) => s + (p.lines_removed || 0), 0) ?? 0
  const avgConf    = result.pages?.length
    ? result.pages.reduce((s, p) => s + (p.confidence || 0), 0) / result.pages.length
    : 0

  const displayText = tab === 'corrected'
    ? editedText
    : result.pages?.map(p => `--- Page ${p.page} ---\n${p.raw_text || p.text}`).join('\n\n') || result.full_text

  async function copy() {
    try { await navigator.clipboard.writeText(displayText) }
    catch {
      const t = document.createElement('textarea')
      t.value = displayText; document.body.appendChild(t); t.select()
      document.execCommand('copy'); document.body.removeChild(t)
    }
    setCopied(true); setTimeout(() => setCopied(false), 2000)
  }

  function handleTextChange(e) {
    setEditedText(e.target.value)
    setIsEdited(e.target.value !== result.full_text)
    setCorrections(null)
  }

  // ── Inline AI correction ────────────────────────────────────────
  async function runAiCorrect() {
    const ta = textareaRef.current
    if (!ta) return
    const start = ta.selectionStart, end = ta.selectionEnd
    const selected = ta.value.slice(start, end).trim()
    if (!selected) return setCorrErr('Select some text first, then click AI Correct.')

    setCorrecting(true); setCorrections(null); setCorrErr(null)
    try {
      const r = await fetch('/correct', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ selected_text: selected }),
      })
      const d = await r.json()
      if (d.error) { setCorrErr(d.error); return }
      setCorrections(d.corrections || [])
    } catch (e) {
      setCorrErr('Request failed: ' + e.message)
    } finally {
      setCorrecting(false)
    }
  }

  function applyCorrections() {
    if (!corrections?.length) return
    let text = editedText
    for (const c of corrections) {
      text = text.replaceAll(c.original, c.corrected)
    }
    setEditedText(text)
    setIsEdited(text !== result.full_text)
    setCorrections(null)
  }

  async function saveToDict() {
    if (!corrections?.length) return
    setSavedDict(false)
    for (const c of corrections) {
      await fetch('/corrections', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ original: c.original, corrected: c.corrected }),
      })
    }
    setSavedDict(true)
    setTimeout(() => setSavedDict(false), 2500)
  }

  // ── Dictionary management ───────────────────────────────────────
  async function loadDict() {
    setDictLoading(true)
    try {
      const r = await fetch('/corrections')
      setDictEntries(await r.json())
    } catch { setDictEntries([]) }
    finally { setDictLoading(false) }
  }

  async function deleteDict(idx) {
    await fetch(`/corrections/${idx}`, { method: 'DELETE' })
    setDictEntries(prev => prev.filter((_, i) => i !== idx))
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
          { v: result.total_pages,                    l: 'Pages'      },
          { v: formatNumber(result.full_text.length), l: 'Characters' },
          { v: docType,                               l: 'Doc Type'   },
          { v: totalFixed,                            l: 'Lines Fixed'},
        ].map(s => (
          <div key={s.l} className="card stat-card">
            <span className="stat-val">{s.v}</span>
            <span className="stat-lbl">{s.l}</span>
          </div>
        ))}
      </div>

      {/* Performance Timings */}
      {result.pages?.[0]?.timings && (() => {
        const sum = result.pages.reduce((a, p) => ({
          pre:  a.pre  + (p.timings?.preprocess_s  || 0),
          tess: a.tess + (p.timings?.tesseract_s   || 0),
          post: a.post + (p.timings?.postprocess_s || 0),
          tot:  a.tot  + (p.timings?.total_s       || 0),
        }), { pre: 0, tess: 0, post: 0, tot: 0 })
        return (
          <div className="card" style={{ marginBottom: '1rem', padding: '1rem' }}>
            <p className="label-cap" style={{ marginBottom: '.6rem' }}>⏱ Processing Time</p>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '.6rem' }}>
              <div style={{ textAlign: 'center', padding: '.5rem', background: 'rgba(255,255,255,.03)', borderRadius: '8px' }}>
                <div style={{ fontSize: '1.3rem', fontWeight: 700, color: 'var(--gold)' }}>{sum.pre.toFixed(1)}s</div>
                <div style={{ fontSize: '.65rem', color: 'var(--txt-3)', marginTop: '.2rem' }}>PREPROCESSING</div>
              </div>
              <div style={{ textAlign: 'center', padding: '.5rem', background: 'rgba(255,255,255,.03)', borderRadius: '8px' }}>
                <div style={{ fontSize: '1.3rem', fontWeight: 700, color: 'var(--gold)' }}>{sum.tess.toFixed(1)}s</div>
                <div style={{ fontSize: '.65rem', color: 'var(--txt-3)', marginTop: '.2rem' }}>TESSERACT OCR</div>
              </div>
              <div style={{ textAlign: 'center', padding: '.5rem', background: 'rgba(255,255,255,.03)', borderRadius: '8px' }}>
                <div style={{ fontSize: '1.3rem', fontWeight: 700, color: 'var(--gold)' }}>{sum.post.toFixed(1)}s</div>
                <div style={{ fontSize: '.65rem', color: 'var(--txt-3)', marginTop: '.2rem' }}>POST-PROCESSING</div>
              </div>
              <div style={{ textAlign: 'center', padding: '.5rem', background: 'rgba(232,160,32,.10)', borderRadius: '8px', border: '1px solid var(--gold-border)' }}>
                <div style={{ fontSize: '1.3rem', fontWeight: 700, color: 'var(--gold-light)' }}>{sum.tot.toFixed(1)}s</div>
                <div style={{ fontSize: '.65rem', color: 'var(--gold)', marginTop: '.2rem', fontWeight: 600 }}>TOTAL TIME</div>
              </div>
            </div>
          </div>
        )
      })()}

      {/* Text output card */}
      <div className="card" style={{ marginBottom: '1rem' }}>
        <div className="result-bar">
          <div style={{ display:'flex', alignItems:'center', gap:'.6rem' }}>
            <div className="tabs">
              <button className={`tab${tab === 'corrected'  ? ' active' : ''}`} onClick={() => setTab('corrected')}>Corrected</button>
              <button className={`tab${tab === 'raw'        ? ' active' : ''}`} onClick={() => setTab('raw')}>Raw OCR</button>
              <button className={`tab${tab === 'highlights' ? ' active' : ''}`} onClick={() => setTab('highlights')}>🔍 Highlights</button>
            </div>
            {isEdited && tab === 'corrected' && <span className="edited-badge">✎ Edited</span>}
          </div>

          <div className="result-actions">
            <button className="btn btn-ghost btn-sm" onClick={copy}>
              {copied ? '✅ Copied!' : '📋 Copy'}
            </button>
            {tab === 'corrected' && (
              <button
                className="btn btn-ghost btn-sm"
                onClick={runAiCorrect}
                disabled={correcting}
                title="Select text in the box below, then click to correct with AI"
              >
                {correcting ? <><span className="spin spin-sm" /> Correcting…</> : '🤖 AI Correct'}
              </button>
            )}
            <a className="btn btn-outline btn-sm" href={`/download/${result.file_id}/txt`}>⬇ TXT</a>
            <a className="btn btn-outline btn-sm" href={`/download/${result.file_id}/docx`}>📝 DOCX</a>
          </div>
        </div>

        {/* Editable textarea (corrected), readonly pre (raw), or highlighted view */}
        {tab === 'corrected' ? (
          <textarea
            ref={textareaRef}
            className="text-edit khmer"
            value={editedText}
            onChange={handleTextChange}
            placeholder="Extracted text will appear here…"
            spellCheck={false}
          />
        ) : tab === 'highlights' ? (
          <>
            <div className="hl-legend">
              <span className="hl-key hl-key-red">🔴 OCR error — click to fix</span>
              <span className="hl-key hl-key-yellow">🟡 Suspicious — click to fix</span>
              {correcting && <span style={{ fontSize: '.65rem', color: 'var(--gold)' }}><span className="spin spin-sm" /> Correcting…</span>}
            </div>
            <HighlightedText
              text={editedText}
              wordConf={wordConf}
              onWordClick={word => {
                setCorrecting(true); setCorrections(null); setCorrErr(null)
                fetch('/correct', {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({ selected_text: word }),
                })
                  .then(r => r.json())
                  .then(d => { if (d.error) setCorrErr(d.error); else setCorrections(d.corrections || []) })
                  .catch(e => setCorrErr('Request failed: ' + e.message))
                  .finally(() => setCorrecting(false))
              }}
            />
          </>
        ) : (
          <div className="text-out">
            <pre className="khmer">{displayText || '—'}</pre>
          </div>
        )}

        {/* AI correction hint */}
        {tab === 'corrected' && !corrections && !corrErr && (
          <p style={{ fontSize:'.68rem', color:'var(--txt-3)', marginTop:'.45rem' }}>
            💡 Select any text above, then click <strong>🤖 AI Correct</strong> to fix errors.
          </p>
        )}
        {tab === 'highlights' && !corrections && !corrErr && !correcting && (
          <p style={{ fontSize:'.68rem', color:'var(--txt-3)', marginTop:'.45rem' }}>
            💡 Click any <span style={{color:'#e05555'}}>🔴 red</span> or <span style={{color:'#d4a800'}}>🟡 yellow</span> word to auto-correct it with AI.
          </p>
        )}

        {/* AI correction error */}
        {corrErr && <p className="warn" style={{ marginTop:'.5rem' }}>⚠️ {corrErr}</p>}

        {/* Correction results panel */}
        {corrections !== null && tab === 'corrected' && (
          <div className="corr-panel">
            <div className="corr-panel-head">
              <span>{corrections.length === 0 ? '✅ No errors found' : `🔍 ${corrections.length} correction(s) found`}</span>
              <button className="btn btn-ghost btn-sm" onClick={() => setCorrections(null)}>✕</button>
            </div>
            {corrections.map((c, i) => (
              <div key={i} className="corr-item">
                <span className="corr-orig">{c.original}</span>
                <span className="corr-new">{c.corrected}</span>
                <span className="corr-reason">{c.reason}</span>
              </div>
            ))}
            {corrections.length > 0 && (
              <div className="corr-apply-btn">
                <button className="btn btn-primary btn-sm" onClick={applyCorrections}>✅ Apply All</button>
                <button className="btn btn-ghost btn-sm" onClick={saveToDict}>
                  {savedDict ? '✅ Saved!' : '📚 Save to Dictionary'}
                </button>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Per-page quality + thumbnails accordion */}
      <div className="card" style={{ padding: 0, overflow: 'hidden', marginBottom: '1rem' }}>
        <button className="accordion-btn" onClick={() => setOpen(!open)}>
          <span>📊 Per-Page Details &amp; Thumbnails</span>
          <span className={`accordion-chevron${open ? ' open' : ''}`}>▼</span>
        </button>
        {open && (
          <div className="quality-grid anim-in">
            {result.pages?.map(p => (
              <div key={p.page} className="card-inner quality-card">
                <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', marginBottom:'.5rem' }}>
                  <h4>📄 Page {p.page}</h4>
                  <ConfBadge score={p.confidence} />
                </div>
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
                {p.thumbnail && (
                  <img
                    src={p.thumbnail}
                    alt={`Page ${p.page} preview`}
                    className="page-thumb"
                    onClick={() => setThumbModal(p.thumbnail)}
                    title="Click to zoom"
                  />
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Custom dictionary panel */}
      <div className="card" style={{ marginBottom: '1.5rem' }}>
        <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between' }}>
          <p className="label-cap" style={{ marginBottom: 0 }}>📚 Custom Correction Dictionary</p>
          <button
            className="btn btn-ghost btn-sm"
            onClick={() => { setShowDict(v => !v); if (!dictEntries) loadDict() }}
          >
            {showDict ? 'Hide' : 'View / Manage'}
          </button>
        </div>
        {showDict && (
          <div className="dict-panel anim-in" style={{ marginTop:'.75rem' }}>
            {dictLoading && <p style={{ fontSize:'.76rem', color:'var(--txt-3)' }}>Loading…</p>}
            {dictEntries?.length === 0 && (
              <p style={{ fontSize:'.76rem', color:'var(--txt-3)' }}>
                No saved corrections yet. Use <strong>🤖 AI Correct</strong> and click <strong>Save to Dictionary</strong>.
              </p>
            )}
            {dictEntries?.map((c, i) => (
              <div key={i} className="dict-row">
                <span className="dict-orig">{c.original}</span>
                <span style={{ color:'var(--txt-3)', fontSize:'.72rem' }}>→</span>
                <span className="dict-corr">{c.corrected}</span>
                <span className="dict-date">{c.added?.slice(0, 10)}</span>
                <button className="btn btn-ghost btn-sm" style={{ marginLeft:'auto', fontSize:'.65rem', padding:'.18rem .45rem' }} onClick={() => deleteDict(i)}>✕</button>
              </div>
            ))}
          </div>
        )}
      </div>

      <button className="btn btn-primary btn-lg" onClick={onReset}>
        📄 Process Another Document
      </button>

      {/* Thumbnail zoom modal */}
      {thumbModal && (
        <div className="thumb-modal-bg" onClick={() => setThumbModal(null)}>
          <img src={thumbModal} alt="Page preview" className="thumb-modal-img" />
        </div>
      )}
    </section>
  )
}
