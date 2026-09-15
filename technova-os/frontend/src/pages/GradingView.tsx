import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { api, ApiError } from '../api'
import { useToast } from '../store'
import { Spinner, Empty } from '../ui'
import type { CodeSubmission } from '../types'

const AXES = [
  { key: 'correctness', label: 'Correctness' },
  { key: 'readability', label: 'Readability' },
  { key: 'efficiency', label: 'Efficiency' },
] as const

export default function GradingView() {
  const { id } = useParams()
  const { push } = useToast()
  const [s, setS] = useState<CodeSubmission | null>(null)
  const [scores, setScores] = useState({ correctness: 3, readability: 3, efficiency: 3 })
  const [comment, setComment] = useState('')

  const load = () => { api.get<CodeSubmission>(`/grading/submissions/${id}`).then(setS).catch(() => setS(null)) }
  useEffect(load, [id])
  if (s === null) return <Spinner />

  const submitReview = async () => {
    try {
      await api.post(`/grading/submissions/${s.id}/review`, { ...scores, comment })
      push('Review submitted! +15 pts 🙌', 'success')
      load()
    } catch (e) { push(e instanceof ApiError ? e.message : 'Failed', 'error') }
  }

  const report = s.auto_report
  const levelColor: Record<string, string> = { error: 'var(--danger)', warn: 'var(--warn)', info: 'var(--text-dim)' }

  return (
    <div>
      <div className="row" style={{ gap: 8, marginBottom: 8 }}>
        <Link to="/grading" className="faint" style={{ fontSize: 13 }}>← Code Review</Link>
      </div>
      <div className="page-head row between wrap" style={{ gap: 12 }}>
        <div>
          <h1 style={{ marginBottom: 4 }}>{s.title}</h1>
          <p className="faint">by {s.author?.name} · {s.language} · <span className={`badge ${s.status === 'graded' ? 'a' : 'p'}`}>{s.status}</span></p>
        </div>
        <div className="glass-card" style={{ padding: '10px 16px', textAlign: 'center' }}>
          <div className="faint" style={{ fontSize: 11, textTransform: 'uppercase' }}>Auto score</div>
          <div style={{ fontSize: 28, fontWeight: 800, color: report.score >= 80 ? 'var(--success)' : report.score >= 50 ? 'var(--warn)' : 'var(--danger)' }}>{report.score}</div>
          {s.status === 'graded' && <div className="faint" style={{ fontSize: 12 }}>Peer: {Math.round(s.final_score)}/100</div>}
        </div>
      </div>

      <div className="grid g2" style={{ gap: 16, alignItems: 'start' }}>
        {/* left: code + automated report */}
        <div>
          {s.description && <p className="faint" style={{ fontSize: 14 }}>{s.description}</p>}
          <pre className="card mono" style={{ overflow: 'auto', fontSize: 13, maxHeight: 420, whiteSpace: 'pre' }}>{s.code}</pre>
          <h3 style={{ margin: '14px 0 8px' }}>Automated report</h3>
          {report.issues.length === 0 ? (
            <div className="card" style={{ color: 'var(--success)' }}>✓ No issues found by static analysis.</div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {report.issues.map((iss, i) => (
                <div key={i} className="card" style={{ padding: '8px 12px', borderLeft: `3px solid ${levelColor[iss.level]}` }}>
                  <span className="badge" style={{ marginRight: 8, textTransform: 'uppercase', fontSize: 10 }}>{iss.level}</span>
                  <span style={{ fontSize: 13 }}>{iss.msg}</span>
                </div>
              ))}
            </div>
          )}
          <div className="faint" style={{ fontSize: 12, marginTop: 8 }}>
            {report.metrics.lines} lines · longest {report.metrics.longest_line} chars
          </div>
        </div>

        {/* right: peer review */}
        <div>
          <h3 style={{ marginTop: 0 }}>Peer review ({s.review_count}/{s.review_goal})</h3>
          {s.can_review ? (
            <div className="card">
              {AXES.map(a => (
                <div key={a.key} style={{ marginBottom: 12 }}>
                  <div className="row between" style={{ fontSize: 13, marginBottom: 4 }}>
                    <span>{a.label}</span><span className="faint">{scores[a.key]}/5</span>
                  </div>
                  <input type="range" min={1} max={5} value={scores[a.key]} style={{ width: '100%' }}
                    onChange={e => setScores({ ...scores, [a.key]: Number(e.target.value) })} />
                </div>
              ))}
              <textarea className="input" rows={3} placeholder="Constructive feedback…" value={comment}
                onChange={e => setComment(e.target.value)} style={{ marginBottom: 10 }} />
              <button className="btn primary" style={{ width: '100%' }} onClick={submitReview}>Submit review (+15 pts)</button>
            </div>
          ) : s.is_author ? (
            <div className="card faint">You can't review your own submission. Wait for peers to review it.</div>
          ) : s.has_reviewed ? (
            <div className="card" style={{ color: 'var(--success)' }}>✓ You've reviewed this submission.</div>
          ) : (
            <div className="card faint">This submission is already graded.</div>
          )}

          {(s.reviews || []).length > 0 && (
            <div style={{ marginTop: 14 }}>
              <div className="faint" style={{ fontSize: 12, textTransform: 'uppercase', letterSpacing: 1, marginBottom: 6 }}>Reviews</div>
              {(s.reviews || []).map((r, i) => (
                <div key={i} className="card" style={{ marginBottom: 8 }}>
                  <div className="row between" style={{ fontSize: 13 }}>
                    <b>{r.reviewer}</b>
                    <span className="faint">C{r.correctness} · R{r.readability} · E{r.efficiency}</span>
                  </div>
                  {r.comment && <p className="faint" style={{ fontSize: 13, margin: '6px 0 0' }}>{r.comment}</p>}
                </div>
              ))}
            </div>
          )}
          {!s.reviews && !s.can_review && <Empty icon="📝" title="No reviews yet" />}
        </div>
      </div>
    </div>
  )
}
