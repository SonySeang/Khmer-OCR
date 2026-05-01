import { useState, useCallback } from 'react'
import Header from './components/Header'
import UploadSection from './components/UploadSection'
import SettingsSection from './components/SettingsSection'
import ProgressSection from './components/ProgressSection'
import ResultsSection from './components/ResultsSection'

const V = { UPLOAD:'upload', SETTINGS:'settings', PROGRESS:'progress', RESULTS:'results' }

export default function App() {
  const [view,    setView]    = useState(V.UPLOAD)
  const [fileId,  setFileId]  = useState(null)
  const [name,    setName]    = useState(null)
  const [size,    setSize]    = useState(null)
  const [preset,  setPreset]  = useState('auto')
  const [useAi,   setUseAi]   = useState(false)
  const [logs,    setLogs]    = useState([])
  const [progress,setProgress]= useState(0)
  const [result,  setResult]  = useState(null)

  const onFileReady = useCallback((id, n, s) => {
    setFileId(id); setName(n); setSize(s); setView(V.SETTINGS)
  }, [])

  const onRemove = useCallback(() => {
    setFileId(null); setName(null); setSize(null); setView(V.UPLOAD)
  }, [])

  const onProcess = useCallback(async () => {
    if (!fileId) return
    setView(V.PROGRESS); setLogs([]); setProgress(0)

    const addLog = msg =>
      setLogs(prev => [...prev.map((l,i) => i===prev.length-1 ? {...l,done:true} : l), { msg, done:false }])

    try {
      const res = await fetch('/process', {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({ file_id:fileId, preset, use_ai:useAi, dpi:300 })
      })
      const reader  = res.body.getReader()
      const decoder = new TextDecoder()
      let buf = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buf += decoder.decode(value, { stream:true })
        const parts = buf.split('\n\n')
        buf = parts.pop()
        for (const part of parts) {
          if (!part.startsWith('data: ')) continue
          try {
            const d = JSON.parse(part.slice(6))
            if (d.message) addLog(d.message)
            if (d.progress !== undefined) setProgress(d.progress)
            if (d.step === 'converting')    setProgress(5)
            if (d.step === 'ai_correction') setProgress(90)
            if (d.step === 'complete' && d.result) {
              setProgress(100)
              setLogs(prev => prev.map(l => ({...l, done:true})))
              setTimeout(() => { setResult(d.result); setView(V.RESULTS) }, 700)
            }
            if (d.step === 'error')
              setLogs(prev => prev.map((l,i) => i===prev.length-1 ? {...l,done:true,error:true} : l))
          } catch { /* skip */ }
        }
      }
    } catch (e) {
      setLogs(prev => [...prev, { msg:'❌ Connection error: '+e.message, done:true, error:true }])
    }
  }, [fileId, preset, useAi])

  const onReset = useCallback(() => {
    setFileId(null); setName(null); setSize(null)
    setPreset('auto'); setUseAi(false)
    setLogs([]); setProgress(0); setResult(null)
    setView(V.UPLOAD)
  }, [])

  return (
    <>
      <Header />
      <main className="page">
        {view === V.UPLOAD   && <UploadSection onFileReady={onFileReady} />}
        {view === V.SETTINGS && <SettingsSection filename={name} fileSize={size} preset={preset} setPreset={setPreset} useAi={useAi} setUseAi={setUseAi} onRemove={onRemove} onProcess={onProcess} />}
        {view === V.PROGRESS && <ProgressSection logs={logs} progress={progress} />}
        {view === V.RESULTS  && result && <ResultsSection result={result} onReset={onReset} />}
      </main>
      <footer className="footer">Khmer OCR Extraction System</footer>
    </>
  )
}
