import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { api } from '../api'
import { useToast } from '../store'
import { Spinner, Modal } from '../ui'

export default function CompetitionView() {
  const { id } = useParams()
  const { push } = useToast()
  const [c, setC] = useState<any>(null)
  const [regForm, setRegForm] = useState({ team_name: '', title: '', summary: '' })
  const [showReg, setShowReg] = useState(false)
  const [scoreEntry, setScoreEntry] = useState<any>(null)
  const [scores, setScores] = useState<Record<string, number>>({})
  const [comment, setComment] = useState('')

  const load = () => api.get(`/competitions/${id}`).then(setC)
  useEffect(() => { load() }, [id])
  if (!c) return <Spinner />

  const act = async (fn: () => Promise<any>, msg: string) => {
    try { await fn(); push(msg, 'success'); load() } catch (e: any) { push(e.message, 'error') }
  }
  const register = () => act(async () => { await api.post(`/competitions/${id}/register`, regForm); setShowReg(false) }, 'Registered!')
  const setStatus = (s: string) => act(() => api.post(`/competitions/${id}/status?status=${s}`), `Status: ${s}`)
  const openScore = (e: any) => { setScoreEntry(e); setScores(Object.fromEntries(c.rubric.map((r: any) => [r.name, 0]))); setComment('') }
  const submitScore = () => act(async () => { await api.post(`/competitions/entries/${scoreEntry.id}/score`, { scores, comment }); setScoreEntry(null) }, 'Score saved')

  const total = Object.values(scores).reduce((a, b) => a + (b || 0), 0)
  const maxTotal = c.rubric.reduce((a: number, r: any) => a + r.max, 0)

  return (
    <div>
      <Link to="/competitions" className="faint" style={{ fontSize: 13 }}>← Competitions</Link>
      <div className="page-head row between" style={{ marginTop: 8 }}>
        <div><h1>{c.title}</h1><div className="row"><span className="badge a">{c.kind}</span>
          <span className={`badge ${c.status === 'open' ? 'g' : c.status === 'judging' ? 'w' : ''}`}>{c.status}</span></div></div>
        <div className="row">
          {c.status === 'open' && <button className="btn primary" onClick={() => setShowReg(true)}>Register entry</button>}
          {c.can_manage && c.status === 'open' && <button className="btn" onClick={() => setStatus('judging')}>Start judging</button>}
          {c.can_manage && c.status === 'judging' && <button className="btn success" onClick={() => setStatus('closed')}>Close & rank</button>}
        </div>
      </div>

      <div className="grid g2">
        <div className="card"><h3 style={{ marginTop: 0 }}>About</h3><p>{c.description}</p>
          <h3>Rubric</h3>
          {c.rubric.map((r: any) => <div key={r.name} className="row between" style={{ padding: '4px 0' }}>
            <span>{r.name}</span><span className="badge">{r.max}</span></div>)}
          <div className="row between" style={{ padding: '8px 0', borderTop: '1px solid var(--border)', marginTop: 6 }}>
            <strong>Total</strong><strong>{maxTotal}</strong></div>
        </div>

        <div className="card"><h3 style={{ marginTop: 0 }}>Entries {c.status === 'closed' && '· Results'}</h3>
          {c.entries.length === 0 && <div className="faint">No entries yet.</div>}
          {c.entries.map((e: any) => (
            <div key={e.id} className="row between" style={{ padding: '10px 0', borderTop: '1px solid var(--border)' }}>
              <div>
                <div className="row">
                  {e.rank && <span className={`badge ${e.rank === 1 ? 'w' : ''}`}>{e.rank === 1 ? '🥇' : e.rank === 2 ? '🥈' : e.rank === 3 ? '🥉' : `#${e.rank}`}</span>}
                  <strong style={{ fontSize: 14 }}>{e.title || e.team_name || 'Entry'}</strong>
                  {e.is_mine && <span className="badge p">You</span>}
                </div>
                <span className="faint" style={{ fontSize: 12 }}>{e.summary}</span>
              </div>
              <div className="row">
                {(c.status !== 'open') && <span className="badge">{e.total_score} pts</span>}
                {c.is_judge && c.status === 'judging' &&
                  <button className="btn sm" onClick={() => openScore(e)}>{e.scored_by_me ? 'Re-score' : 'Score'}</button>}
              </div>
            </div>
          ))}
        </div>
      </div>

      {showReg && (
        <Modal title="Register your entry" onClose={() => setShowReg(false)}>
          <label className="field"><span>Team name</span><input className="input" value={regForm.team_name} onChange={e => setRegForm({ ...regForm, team_name: e.target.value })} /></label>
          <label className="field"><span>Project / entry title</span><input className="input" value={regForm.title} onChange={e => setRegForm({ ...regForm, title: e.target.value })} /></label>
          <label className="field"><span>Summary</span><textarea className="input" rows={3} value={regForm.summary} onChange={e => setRegForm({ ...regForm, summary: e.target.value })} /></label>
          <div className="row" style={{ justifyContent: 'flex-end' }}><button className="btn primary" onClick={register}>Register</button></div>
        </Modal>
      )}

      {scoreEntry && (
        <Modal title={`Score: ${scoreEntry.title || scoreEntry.team_name}`} onClose={() => setScoreEntry(null)}>
          {c.rubric.map((r: any) => (
            <label className="field" key={r.name}>
              <span>{r.name} (0–{r.max}) — {scores[r.name] || 0}</span>
              <input type="range" min={0} max={r.max} value={scores[r.name] || 0} style={{ width: '100%' }}
                onChange={e => setScores({ ...scores, [r.name]: Number(e.target.value) })} />
            </label>
          ))}
          <label className="field"><span>Comment</span><textarea className="input" rows={2} value={comment} onChange={e => setComment(e.target.value)} /></label>
          <div className="row between"><strong>Total: {total}/{maxTotal}</strong>
            <button className="btn primary" onClick={submitScore}>Save score</button></div>
        </Modal>
      )}
    </div>
  )
}
