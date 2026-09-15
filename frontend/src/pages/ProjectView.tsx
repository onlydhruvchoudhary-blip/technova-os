import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { api } from '../api'
import { useAuth, useToast } from '../store'
import { Spinner, StateBadge, Avatar, Modal } from '../ui'

const TASK_STATES = ['Backlog', 'To Do', 'In Progress', 'Review', 'Testing', 'Done']

export default function ProjectView() {
  const { slug } = useParams()
  const { user } = useAuth()
  const { push } = useToast()
  const [p, setP] = useState<any>(null)
  const [tab, setTab] = useState('overview')
  const [matches, setMatches] = useState<any>(null)
  const [newTask, setNewTask] = useState('')
  const [reviewForm, setReviewForm] = useState({ stage: '', score: 8, feedback: '' })
  const [err, setErr] = useState('')

  const load = () => api.get(`/projects/${slug}`).then(setP).catch(e => setErr(e.message))
  useEffect(() => { load() }, [slug])
  useEffect(() => { if (tab === 'team') api.get(`/projects/${slug}/matches`).then(setMatches) }, [tab])

  if (err) return <div className="card"><h3>🔒 {err}</h3><Link className="btn" to="/projects">Back to projects</Link></div>
  if (!p) return <Spinner />

  const isMentor = ['MENTOR', 'ADVISOR', 'CLUB_HEAD', 'SUPER_ADMIN'].includes(user!.role)
  const isOwner = p.owner_id === user!.id
  const idx = p.state_order.indexOf(p.state)

  const act = async (fn: () => Promise<any>, msg: string) => {
    try { await fn(); push(msg, 'success'); load() } catch (e: any) { push(e.message, 'error') }
  }
  const advance = () => {
    const next = p.state_order[idx + 1]
    if (next) act(() => api.post(`/projects/${slug}/state?state=${next}`), `Moved to ${next}`)
  }
  const addTask = () => { if (newTask) act(async () => { await api.post(`/projects/${slug}/tasks`, { title: newTask, status: 'Backlog' }); setNewTask('') }, 'Task added') }
  const moveTask = (t: any, dir: number) => {
    const ni = TASK_STATES.indexOf(t.status) + dir
    if (ni >= 0 && ni < TASK_STATES.length) act(() => api.patch(`/tasks/${t.id}`, { status: TASK_STATES[ni] }), 'Task moved')
  }
  const submitReview = () => act(async () => { await api.post(`/projects/${slug}/reviews`, reviewForm); setReviewForm({ stage: '', score: 8, feedback: '' }) }, 'Review submitted')

  return (
    <div>
      <Link to="/projects" className="faint" style={{ fontSize: 13 }}>← Projects</Link>
      <div className="page-head row between" style={{ marginTop: 8 }}>
        <div><h1>{p.title}</h1><div className="row"><StateBadge state={p.state} />
          <span className="faint">👥 {p.member_count}/{p.team_size} members</span></div></div>
        {p.can_manage && idx < p.state_order.length - 1 && (
          <button className="btn primary" onClick={advance}>Advance → {p.state_order[idx + 1]}</button>)}
        {!p.is_member && !isOwner && (
          <button className="btn" onClick={() => act(() => api.post(`/projects/${slug}/join`), 'Join request sent')}>Request to join</button>)}
      </div>

      {/* pipeline */}
      <div className="card" style={{ marginBottom: 16, overflowX: 'auto' }}>
        <div className="tier-track" style={{ minWidth: 640 }}>
          {p.state_order.map((s: string, i: number) => (
            <div key={s} className={`tier-node ${i <= idx ? 'reached' : ''}`} style={{ fontSize: 10 }}>{s.replace('_', ' ')}</div>
          ))}
        </div>
      </div>

      <div className="row" style={{ marginBottom: 16, flexWrap: 'wrap' }}>
        {['overview', 'tasks', 'team', 'reviews'].map(t =>
          <button key={t} className={`btn sm ${tab === t ? 'primary' : 'ghost'}`} onClick={() => setTab(t)}>{t[0].toUpperCase() + t.slice(1)}</button>)}
      </div>

      {tab === 'overview' && (
        <div className="grid g2">
          <div className="card"><h3 style={{ marginTop: 0 }}>Problem</h3><p>{p.problem || '—'}</p>
            <h3>Solution</h3><p>{p.solution || '—'}</p>
            {p.description && <><h3>Description</h3><p>{p.description}</p></>}</div>
          <div className="card"><h3 style={{ marginTop: 0 }}>Details</h3>
            <div className="row wrap" style={{ gap: 6, marginBottom: 12 }}>
              {(p.tech || []).map((t: string) => <span key={t} className="badge a">{t}</span>)}</div>
            <div className="faint" style={{ fontSize: 13 }}>Required skills: {(p.required_skills || []).join(', ') || '—'}</div>
            {p.repo_url && <div style={{ marginTop: 10 }}><a className="btn sm" href={p.repo_url} target="_blank" rel="noreferrer">↗ Repository</a></div>}
            {p.demo_url && <div style={{ marginTop: 8 }}><a className="btn sm" href={p.demo_url} target="_blank" rel="noreferrer">▶ Live demo</a></div>}
          </div>
        </div>
      )}

      {tab === 'tasks' && (
        <div>
          {p.is_member && (
            <div className="row" style={{ marginBottom: 14 }}>
              <input className="input" placeholder="New task…" value={newTask} onChange={e => setNewTask(e.target.value)} />
              <button className="btn primary" onClick={addTask}>Add</button>
            </div>
          )}
          <div className="kanban">
            {TASK_STATES.map(st => (
              <div className="kcol" key={st}>
                <h4>{st} ({p.tasks.filter((t: any) => t.status === st).length})</h4>
                {p.tasks.filter((t: any) => t.status === st).map((t: any) => (
                  <div className="ktask" key={t.id}>
                    <div>{t.title}</div>
                    {p.is_member && (
                      <div className="row" style={{ marginTop: 6, gap: 4 }}>
                        <button className="btn ghost sm" style={{ padding: '2px 6px' }} onClick={() => moveTask(t, -1)}>←</button>
                        <button className="btn ghost sm" style={{ padding: '2px 6px' }} onClick={() => moveTask(t, 1)}>→</button>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            ))}
          </div>
        </div>
      )}

      {tab === 'team' && (
        <div className="grid g2">
          <div className="card"><h3 style={{ marginTop: 0 }}>Team</h3>
            {p.members.map((m: any) => (
              <div key={m.user_id} className="row between" style={{ padding: '8px 0' }}>
                <div className="row"><Avatar seed={m.avatar_seed} name={m.name} size={32} />
                  <div><div style={{ fontWeight: 600, fontSize: 14 }}>{m.name}</div>
                    <span className="faint" style={{ fontSize: 12 }}>{m.role}</span></div></div>
                {m.status === 'requested'
                  ? (p.can_manage ? <button className="btn success sm" onClick={() => act(() => api.post(`/projects/${slug}/members/${m.user_id}/approve`), 'Approved')}>Approve</button>
                    : <span className="badge w">Pending</span>)
                  : <span className="badge g">Member</span>}
              </div>
            ))}
          </div>
          <div className="card"><h3 style={{ marginTop: 0 }}>🤝 Suggested teammates</h3>
            <p className="faint" style={{ fontSize: 13 }}>Ranked by complementary skills — explainable, based on real skill data.</p>
            {!matches ? <Spinner /> : matches.candidates.length === 0
              ? <div className="faint">No strong matches yet.</div>
              : matches.candidates.map((c: any) => (
                <div key={c.user_id} style={{ padding: '10px 0', borderTop: '1px solid var(--border)' }}>
                  <div className="row between"><div className="row"><Avatar seed={c.avatar_seed} name={c.name} size={30} />
                    <strong style={{ fontSize: 14 }}>{c.name}</strong></div><span className="badge p">match {c.score}</span></div>
                  {c.reasons.map((r: string, i: number) => <div key={i} className="faint" style={{ fontSize: 12, marginTop: 4 }}>• {r}</div>)}
                </div>
              ))}
          </div>
        </div>
      )}

      {tab === 'reviews' && (
        <div className="grid g2">
          <div className="card"><h3 style={{ marginTop: 0 }}>Mentor reviews</h3>
            {p.reviews.length === 0 && <div className="faint">No reviews yet.</div>}
            {p.reviews.map((r: any) => (
              <div key={r.id} style={{ padding: '10px 0', borderTop: '1px solid var(--border)' }}>
                <div className="row between"><span className="badge">{r.stage || 'Review'}</span><span className="badge p">{r.score}/10</span></div>
                <p style={{ margin: '6px 0 0' }}>{r.feedback}</p>
                <span className="faint" style={{ fontSize: 11 }}>{new Date(r.created_at).toLocaleDateString()}</span>
              </div>
            ))}
          </div>
          {isMentor && (
            <div className="card"><h3 style={{ marginTop: 0 }}>Add a review</h3>
              <label className="field"><span>Stage</span>
                <input className="input" value={reviewForm.stage} onChange={e => setReviewForm({ ...reviewForm, stage: e.target.value })} placeholder="e.g. PLANNING" /></label>
              <label className="field"><span>Score (0-10)</span>
                <input className="input" type="number" min={0} max={10} value={reviewForm.score} onChange={e => setReviewForm({ ...reviewForm, score: Number(e.target.value) })} /></label>
              <label className="field"><span>Feedback</span>
                <textarea className="input" rows={3} value={reviewForm.feedback} onChange={e => setReviewForm({ ...reviewForm, feedback: e.target.value })} /></label>
              <button className="btn primary" onClick={submitReview} disabled={!reviewForm.feedback}>Submit review</button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
