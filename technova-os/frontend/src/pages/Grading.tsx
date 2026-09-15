import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, ApiError } from '../api'
import { useToast } from '../store'
import { Spinner, Empty, Modal, Avatar } from '../ui'
import type { CodeSubmission } from '../types'
import CodeEditor from '../CodeEditor'

export default function Grading() {
  const { push } = useToast()
  const [subs, setSubs] = useState<CodeSubmission[] | null>(null)
  const [filter, setFilter] = useState<'all' | 'open' | 'graded' | 'mine'>('all')
  const [show, setShow] = useState(false)
  const [form, setForm] = useState({ title: '', language: 'python', code: '', description: '' })

  const load = () => { api.get<CodeSubmission[]>('/grading/submissions').then(setSubs).catch(() => setSubs([])) }
  useEffect(load, [])
  if (!subs) return <Spinner />

  const shown = subs.filter(s =>
    filter === 'all' ? true : filter === 'mine' ? s.is_author : s.status === filter)

  const create = async () => {
    try {
      const s = await api.post<CodeSubmission>('/grading/submissions', form)
      push(`Submitted! Auto-score ${s.auto_score}/100 🎓`, 'success')
      setShow(false); setForm({ title: '', language: 'python', code: '', description: '' }); load()
    } catch (e) { push(e instanceof ApiError ? e.message : 'Failed', 'error') }
  }

  return (
    <div>
      <div className="page-head row between wrap" style={{ gap: 12 }}>
        <div><h1>Code Review 🎓</h1><p>Submit code for automated checks + rubric-based peer review. Earn points when it's graded.</p></div>
        <button className="btn primary" onClick={() => setShow(true)}>+ Submit code</button>
      </div>

      <div className="row wrap" style={{ gap: 6, marginBottom: 16 }}>
        {(['all', 'open', 'graded', 'mine'] as const).map(f => (
          <button key={f} className={`btn sm ${filter === f ? 'primary' : 'ghost'}`} onClick={() => setFilter(f)}>
            {f === 'all' ? 'All' : f === 'mine' ? 'My submissions' : f[0].toUpperCase() + f.slice(1)}
          </button>
        ))}
      </div>

      {shown.length === 0 ? <Empty icon="🎓" title="No submissions here" sub="Submit code to get it reviewed." /> : (
        <div className="grid g2">
          {shown.map(s => (
            <Link key={s.id} to={`/grading/${s.id}`} className="card" style={{ display: 'block' }}>
              <div className="row between" style={{ marginBottom: 6 }}>
                <span className={`badge ${s.status === 'graded' ? 'a' : 'p'}`}>{s.status}</span>
                <span className="badge">{s.language}</span>
              </div>
              <h3 style={{ margin: '0 0 6px' }}>{s.title}</h3>
              <div className="row between wrap" style={{ gap: 8, marginTop: 8 }}>
                <div className="row" style={{ gap: 8 }}>
                  {s.author && <Avatar seed={s.author.avatar_seed} name={s.author.name} size={24} />}
                  <span className="faint" style={{ fontSize: 12 }}>{s.author?.name}</span>
                </div>
                <div className="row" style={{ gap: 10 }}>
                  <ScorePill label="Auto" value={s.auto_score} />
                  {s.status === 'graded'
                    ? <ScorePill label="Peer" value={Math.round(s.final_score)} />
                    : <span className="faint" style={{ fontSize: 12 }}>{s.review_count}/{s.review_goal} reviews</span>}
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}

      {show && (
        <Modal title="Submit code for review" onClose={() => setShow(false)} wide>
          <label className="field"><span>Title</span>
            <input className="input" value={form.title} onChange={e => setForm({ ...form, title: e.target.value })} /></label>
          <div className="grid g2">
            <label className="field"><span>Language</span>
              <select className="input" value={form.language} onChange={e => setForm({ ...form, language: e.target.value })}>
                {['python', 'javascript', 'typescript', 'java', 'c++', 'other'].map(l => <option key={l} value={l}>{l}</option>)}
              </select></label>
            <label className="field"><span>Short description</span>
              <input className="input" value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} /></label>
          </div>
          <label className="field"><span>Code</span>
            <CodeEditor value={form.code} onChange={code => setForm({ ...form, code })} minHeight={240} /></label>
          <div className="row" style={{ justifyContent: 'flex-end' }}>
            <button className="btn primary" onClick={create} disabled={!form.title.trim() || !form.code.trim()}>Run checks & submit</button>
          </div>
        </Modal>
      )}
    </div>
  )
}

function ScorePill({ label, value }: { label: string; value: number }) {
  const color = value >= 80 ? 'var(--success)' : value >= 50 ? 'var(--warn)' : 'var(--danger)'
  return (
    <div style={{ textAlign: 'center' }}>
      <div style={{ fontWeight: 800, color }}>{value}</div>
      <div className="faint" style={{ fontSize: 10, textTransform: 'uppercase' }}>{label}</div>
    </div>
  )
}
