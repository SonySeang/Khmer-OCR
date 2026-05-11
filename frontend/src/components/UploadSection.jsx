import { useEffect, useRef, useState } from 'react'
import { formatSize } from '../utils/format'

const ACCEPT = '.pdf,.jpg,.jpeg,.png,.tiff,.tif,.bmp,.webp'

export default function UploadSection({ onFileReady, onBatchReady }) {
  const [docs,      setDocs]      = useState(null)
  const [uploading, setUploading] = useState(false)
  const [over,      setOver]      = useState(false)
  const [error,     setError]     = useState(null)
  const [queue,     setQueue]     = useState([])   // pending multi-upload list
  const inputRef = useRef(null)

  useEffect(() => {
    fetch('/documents').then(r => r.json()).then(setDocs).catch(() => setDocs([]))
  }, [])

  function showError(msg) { setError(msg); setTimeout(() => setError(null), 4000) }

  async function uploadOne(file) {
    const fd = new FormData()
    fd.append('file', file)
    const r = await fetch('/upload', { method: 'POST', body: fd })
    const d = await r.json()
    if (d.error) throw new Error(d.error)
    return { file_id: d.file_id, filename: d.filename, size: d.size }
  }

  async function handleFiles(files) {
    const fileList = Array.from(files)
    if (fileList.length === 0) return

    // Validate all files first
    for (const f of fileList) {
      const ok = /\.(pdf|jpg|jpeg|png|tiff?|bmp|webp)$/i.test(f.name)
      if (!ok) return showError(`Unsupported file: ${f.name}`)
      if (f.size > 50 * 1024 * 1024) return showError(`File too large: ${f.name} (max 50 MB)`)
    }

    setUploading(true)
    try {
      if (fileList.length === 1) {
        const result = await uploadOne(fileList[0])
        onFileReady(result.file_id, result.filename, result.size)
      } else {
        // Batch: upload all, show queue
        setQueue(fileList.map(f => ({ name: f.name, size: f.size, status: 'uploading' })))
        const uploaded = []
        for (let i = 0; i < fileList.length; i++) {
          const result = await uploadOne(fileList[i])
          uploaded.push(result)
          setQueue(prev => prev.map((q, idx) => idx === i ? { ...q, status: 'done' } : q))
        }
        onBatchReady(uploaded)
      }
    } catch (e) {
      showError(e.message || 'Upload failed. Please try again.')
    } finally {
      setUploading(false)
      setQueue([])
    }
  }

  async function pickDoc(name) {
    try {
      const r = await fetch('/process-local', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
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
        <p>PDF, JPG, PNG, TIFF, BMP or WEBP · Max 50 MB · Select multiple for batch</p>
      </div>

      {error && <p className="warn" style={{ marginBottom: '1rem' }}>⚠️ {error}</p>}

      <div className="upload-grid">
        {/* Drop zone */}
        <div
          className={`dropzone${over ? ' over' : ''}`}
          onClick={() => !uploading && inputRef.current?.click()}
          onDragOver={e => { e.preventDefault(); setOver(true) }}
          onDragLeave={() => setOver(false)}
          onDrop={e => { e.preventDefault(); setOver(false); !uploading && handleFiles(e.dataTransfer.files) }}
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
          <p className="dz-title">{uploading ? 'Uploading…' : 'Drop files here'}</p>
          <p className="dz-hint">or click to browse · hold Ctrl/⌘ for multiple files</p>
          <input
            ref={inputRef} type="file" accept={ACCEPT} hidden multiple
            onChange={e => e.target.files.length && handleFiles(e.target.files)}
          />
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

      {/* Upload queue (multi-file) */}
      {queue.length > 0 && (
        <div className="queue-list">
          {queue.map((q, i) => (
            <div key={i} className="queue-item">
              <span>{q.status === 'done' ? '✅' : <span className="spin spin-sm" />}</span>
              <span className="queue-item-name">{q.name}</span>
              <span className="queue-item-size">{formatSize(q.size)}</span>
            </div>
          ))}
        </div>
      )}
    </section>
  )
}
