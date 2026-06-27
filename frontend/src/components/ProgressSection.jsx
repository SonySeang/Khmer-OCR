export default function ProgressSection({ logs, progress }) {
  const done = progress === 100

  return (
    <section className="anim-up">
      <div className="progress-header">
        {done
          ? <span style={{ fontSize:'1.5rem' }}>✅</span>
          : <div className="spin spin-md" />
        }
        <div>
          <p className="progress-title">{done ? 'Done!' : 'Processing…'}</p>
          <p className="progress-sub">Extracting Khmer text from your document</p>
        </div>
        <div className="progress-pct">{progress}%</div>
      </div>

      <div className="card">
        <div className="pbar-wrap">
          <div className="pbar" style={{ width:`${progress}%` }} />
        </div>

        <div className="card-inner log-scroll">
          {logs.length === 0 && (
            <p style={{ fontSize:'.78rem', color:'var(--txt-3)' }}>Starting…</p>
          )}
          {logs.map((l, i) => (
            <div key={i} className={`log-line ${l.done ? (l.error ? 'err' : 'done') : 'pending'}`}>
              <span className="log-icon">
                {l.done
                  ? <span style={{ fontSize:'.72rem', color: l.error ? 'var(--red)' : 'var(--green)' }}>{l.error ? '✕' : '✓'}</span>
                  : <span className="spin spin-sm" />
                }
              </span>
              <span className="log-msg">{l.msg}</span>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
