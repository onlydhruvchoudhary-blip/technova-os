import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { api } from '../api'
import { useToast } from '../store'
import { Spinner, DiffBadge } from '../ui'

export default function ChallengeView() {
  const { slug } = useParams()
  const { push } = useToast()
  const [ch, setCh] = useState<any>(null)
  const [code, setCode] = useState('')
  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState<any>(null)

  useEffect(() => { api.get(`/challenges/${slug}`).then(c => { setCh(c); setCode(c.last_code || c.starter_code) }) }, [slug])
  if (!ch) return <Spinner />

  const submit = async () => {
    setBusy(true); setResult(null)
    try {
      const r = await api.post(`/challenges/${slug}/submit`, { code })
      setResult(r)
      if (r.passed) {
        const effects = r.effects || []
        const pts = effects.flatMap((e: any) => e.points?.awarded ? [e.points.awarded] : [])
        push(`Accepted! ${pts.length ? `+${pts[0]} points` : ''} 🎉`, 'success')
      } else push('Not quite — check the feedback.', 'error')
      const fresh = await api.get(`/challenges/${slug}`); setCh(fresh)
    } catch (e: any) { push(e.message, 'error') } finally { setBusy(false) }
  }

  return (
    <div>
      <Link to="/challenges" className="faint" style={{ fontSize: 13 }}>← Challenges</Link>
      <div className="page-head" style={{ marginTop: 8 }}>
        <div className="row between">
          <h1>{ch.title}</h1>
          <div className="row"><DiffBadge d={ch.difficulty} /><span className="badge p">+{ch.points} pts</span>
            {ch.solved && <span className="badge g">✓ Solved</span>}</div>
        </div>
      </div>

      <div className="grid" style={{ gridTemplateColumns: '1fr 1.2fr', gap: 18 }}>
        <div className="card">
          <h3 style={{ marginTop: 0 }}>Problem</h3>
          <p style={{ whiteSpace: 'pre-wrap' }}>{ch.statement}</p>
          <h4>Function signature</h4>
          <code className="mono" style={{ background: 'var(--bg-2)', padding: '4px 8px', borderRadius: 6 }}>{ch.function_name}(…)</code>
          <h4 style={{ marginTop: 16 }}>Sample tests</h4>
          {ch.sample_tests.map((t: any, i: number) => (
            <div key={i} className="test-row">
              <span className="faint">in:</span> {JSON.stringify(t.args)}
              <span className="faint">→</span> {JSON.stringify(t.expected)}
            </div>
          ))}
          <p className="faint" style={{ fontSize: 12, marginTop: 10 }}>
            🔒 {ch.hidden_test_count} hidden tests will also run. Your code executes in an isolated sandbox with a time limit.
          </p>
        </div>

        <div>
          <textarea className="code-editor" value={code} onChange={e => setCode(e.target.value)} spellCheck={false} />
          <div className="row" style={{ marginTop: 12, justifyContent: 'flex-end' }}>
            <button className="btn" onClick={() => setCode(ch.starter_code)}>Reset</button>
            <button className="btn primary" onClick={submit} disabled={busy}>{busy ? 'Judging…' : 'Submit'}</button>
          </div>

          {result && (
            <div className="card" style={{ marginTop: 14, borderColor: result.passed ? 'var(--success)' : 'var(--danger)' }}>
              <div className="row between">
                <h3 style={{ margin: 0 }}>{result.passed ? '✅ Accepted' : '❌ Not accepted'}</h3>
                <span className="badge">{result.tests_passed}/{result.tests_total} tests passed</span>
              </div>
              <p className="muted" style={{ marginBottom: 8 }}>{result.feedback}</p>
              {result.sample_results.map((r: any, i: number) => (
                <div key={i} className="test-row" style={{ borderLeft: `3px solid ${r.ok ? 'var(--success)' : 'var(--danger)'}` }}>
                  <span className="faint">in</span> {JSON.stringify(r.args)}
                  <span className="faint">exp</span> {JSON.stringify(r.expected)}
                  <span className="faint">got</span> {r.got}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
