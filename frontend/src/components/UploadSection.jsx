import { useEffect, useRef, useState } from 'react'
import { formatSize } from '../utils/format'

export default function UploadSection({ onFileReady }) {
  const [docs, setDocs]         = useState(null)
  const [uploading, setUploading] = useState(false)
  const [over, setOver]         = useState(false)
  const [error, setError]       = useState(null)
  const inputRef                = useRef(null)

  useEffect(() => {
    fetch('/documents').then(r => r.json()).then(setDocs).catch(() => setDocs([]))
  }, [])

  function showError(msg) { setError(msg); setTimeout(() => setError(null), 4000) }

  async function handleFile(file) {
    if (!file.name.toLowerCase().endsWith('.pdf')) return showError('Please upload a PDF file.')
    if (file.size > 20 * 1024 * 1024) return showError('File too large. Max 20MB.')
    setUploading(true)
    const fd = new FormData()
    fd.append('file', file)
    try {
      const r = await fetch('/upload', { method: 'POST', body: fd })
      const d = await r.json()
      if (d.error) return showError(d.error)
      onFileReady(d.file_id, d.filename, d.size)
    } catch { showError('Upload failed. Please try again.') }
    finally { setUploading(false) }
  }

  async function pickDoc(name) {
    try {
      const r = await fetch('/process-local', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filename: name })
      })
      const d = await r.json()
      if (d.error) return showError(d.error)
      onFileReady(d.file_id, d.filename, d.size)
    } catch { showError('Failed to select document.') }
  }

  return (
    <section className="anim-up">
      <div className="sh">
        <h2>Upload Document</h2>
        <p>Drag & drop a PDF or pick from your existing documents</p>
      </div>

      {error && <p className="warn" style={{ marginBottom: '1rem' }}>⚠️ {error}</p>}

      <div className="upload-grid">
        {/* Drop zone */}
        <div
          className={`dropzone${over ? ' over' : ''}`}
          onClick={() => !uploading && inputRef.current?.click()}
          onDragOver={e => { e.preventDefault(); setOver(true) }}
          onDragLeave={() => setOver(false)}
          onDrop={e => { e.preventDefault(); setOver(false); e.dataTransfer.files[0] && handleFile(e.dataTransfer.files[0]) }}
        >
          {uploading ? (
            <div className="spin spin-lg" />
          ) : (
            <div className="dz-icon">
              <svg width="46" height="46" viewBox="0 0 48 48" fill="none">
                <path d="M24 4v28M24 4L16 12M24 4l8 8" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/>
                <path d="M8 28v10a4 4 0 0 0 4 4h24a4 4 0 0 0 4-4V28" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"/>
              </svg>
            </div>
          )}
          <p className="dz-title">{uploading ? 'Uploading…' : 'Drop your PDF here'}</p>
          <p className="dz-hint">or click to browse · Max 20MB</p>
          <input ref={inputRef} type="file" accept=".pdf" hidden
            onChange={e => e.target.files[0] && handleFile(e.target.files[0])} />
        </div>

        {/* Doc list */}
        <div className="card">
          <p className="label-cap" style={{ marginBottom: '.65rem' }}>Your Documents</p>
          <div className="doc-list">
            {docs === null && <p style={{ fontSize:'.78rem', color:'var(--txt-3)', padding:'.75rem 0', textAlign:'center' }}>Loading…</p>}
            {docs?.length === 0 && <p style={{ fontSize:'.78rem', color:'var(--txt-3)', padding:'.75rem 0', textAlign:'center' }}>No PDFs in Document/ folder</p>}
            {docs?.map(d => (
              <button key={d.name} className="doc-item" onClick={() => pickDoc(d.name)}>
                <span>📄</span>
                <span className="doc-name">{d.name}</span>
                <span className="doc-size">{formatSize(d.size)}</span>
              </button>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}
